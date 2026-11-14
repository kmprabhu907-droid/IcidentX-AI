"""
INCIDENTX AI - Centralized Environment Manager (Phase 8.1)
Coordinates infrastructure adapters, manages active environment context,
validates connection health, and enforces strict operational isolation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.infrastructure.core.base_adapter import BaseInfrastructureAdapter
from backend.app.infrastructure.core.environment_context import EnvironmentContext
from backend.app.infrastructure.core.environment_registry import environment_registry
from backend.app.infrastructure.core.infrastructure_models import (
    ConnectionStatus,
    EnvironmentHealth,
    EnvironmentMetadata,
    EnvironmentMode,
    InfrastructureEvent,
    InfrastructureService,
    InfrastructureWorkload,
    ResourceMetric,
    WorkloadStatus,
)
from backend.app.infrastructure.security.environment_access_policy import EnvironmentAccessPolicy
from backend.app.models.user import User


class EnvironmentConnectionException(IncidentXException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=503, details=details)


class EnvironmentManager:
    """
    Centralized Controller for Hybrid Infrastructure Environments.
    Enforces explicit environment selection without silent fallbacks.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._active_mode: EnvironmentMode = EnvironmentMode.DEMOMESH
        self._last_error: Optional[str] = None
        self.registry = environment_registry

    @property
    def active_mode(self) -> EnvironmentMode:
        return self._active_mode

    @property
    def current_mode(self) -> EnvironmentMode:
        return self._active_mode

    @property
    def active_adapter(self) -> BaseInfrastructureAdapter:
        return self.get_active_adapter()

    def get_active_adapter(self) -> BaseInfrastructureAdapter:
        """Retrieves the adapter corresponding to the currently active environment."""
        adapter = environment_registry.get_adapter(self._active_mode)
        if not adapter:
            raise EnvironmentConnectionException(
                f"No infrastructure adapter registered for active mode: '{self._active_mode.value}'"
            )
        return adapter

    async def initialize(self) -> None:
        """Initializes default DemoMesh environment upon server startup."""
        async with self._lock:
            adapter = self.get_active_adapter()
            await adapter.connect()
            EnvironmentContext.set_current_mode(self._active_mode)
            logger.info(f"[EnvironmentManager] Initialized in '{self._active_mode.value}' mode.")

    async def list_environments(self) -> List[EnvironmentMetadata]:
        """Returns metadata for all registered environments."""
        metas = []
        for mode in environment_registry.list_available_modes():
            adapter = environment_registry.get_adapter(mode)
            if adapter:
                try:
                    meta = await adapter.get_environment_metadata()
                    metas.append(meta)
                except Exception as e:
                    metas.append(
                        EnvironmentMetadata(
                            mode=mode,
                            cluster_name=f"{mode.value.lower()}-cluster",
                            api_endpoint="unreachable",
                            version="unknown",
                            connection_status=ConnectionStatus.ERROR,
                            is_read_only=True,
                            connection_error=str(e),
                        )
                    )
        return metas

    async def get_active_environment_metadata(self) -> EnvironmentMetadata:
        """Returns metadata for the currently selected active environment."""
        adapter = self.get_active_adapter()
        return await adapter.get_environment_metadata()

    async def switch_environment(
        self, target_mode: EnvironmentMode, user: Optional[User] = None
    ) -> EnvironmentMetadata:
        """
        Explicitly switches the active environment.
        Enforces RBAC authorization and attempts live connection.
        NEVER silently falls back to DemoMesh if Kubernetes connection fails.
        """
        # 1. Enforce RBAC permission checks
        EnvironmentAccessPolicy.assert_can_switch(user)

        async with self._lock:
            if target_mode == self._active_mode:
                return await self.get_active_environment_metadata()

            logger.info(
                f"[EnvironmentManager] User '{getattr(user, 'email', 'system')}' switching "
                f"from {self._active_mode.value} to {target_mode.value}"
            )

            # 2. Get target adapter
            target_adapter = environment_registry.get_adapter(target_mode)
            if not target_adapter:
                raise EnvironmentConnectionException(
                    f"No adapter available for requested environment mode: '{target_mode.value}'"
                )

            # 3. Attempt live connection
            connected = await target_adapter.connect()
            if not connected:
                # Retrieve connection error
                meta = await target_adapter.get_environment_metadata()
                err_msg = meta.connection_error or "Unknown connection failure"
                self._last_error = err_msg

                # STRICT RULE: NEVER silently fall back! Raise explicit error
                raise EnvironmentConnectionException(
                    message=f"Failed to connect to '{target_mode.value}' cluster. Explicit error: {err_msg}",
                    details={
                        "target_mode": target_mode.value,
                        "connection_status": ConnectionStatus.ERROR.value,
                        "error": err_msg,
                        "remediation": "Check cluster reachability, API server endpoint, and Bearer token permissions.",
                    },
                )

            # 4. Safely disconnect previous adapter if changing modes
            old_adapter = self.get_active_adapter()
            try:
                await old_adapter.disconnect()
            except Exception as e:
                logger.warning(f"[EnvironmentManager] Disconnect error on previous adapter: {e}")

            # 5. Commit state transition
            self._active_mode = target_mode
            self._last_error = None
            EnvironmentContext.set_current_mode(target_mode)

            logger.info(f"[EnvironmentManager] Successfully transitioned to active environment: '{target_mode.value}'")
            return await target_adapter.get_environment_metadata()

    async def check_health(self) -> EnvironmentHealth:
        """Checks health of the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.health_check()

    async def list_services(self) -> List[InfrastructureService]:
        """Lists services discovered in the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.list_services()

    async def list_workloads(self, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        """Lists workloads in the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.list_workloads(namespace=namespace)

    async def get_workload_status(
        self, workload_id: str, namespace: Optional[str] = None
    ) -> Optional[WorkloadStatus]:
        """Gets workload status from the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.get_workload_status(workload_id=workload_id, namespace=namespace)

    async def get_events(
        self, limit: int = 50, namespace: Optional[str] = None
    ) -> List[InfrastructureEvent]:
        """Gets cluster/mesh events from the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.get_events(limit=limit, namespace=namespace)

    async def get_metrics(
        self, workload_id: Optional[str] = None
    ) -> List[ResourceMetric]:
        """Gets metrics from the active environment."""
        adapter = self.get_active_adapter()
        return await adapter.get_resource_metrics(workload_id=workload_id)


# Central singleton instance
environment_manager = EnvironmentManager()
