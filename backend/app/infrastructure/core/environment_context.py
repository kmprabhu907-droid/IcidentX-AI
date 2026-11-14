"""
INCIDENTX AI - Environment Context Manager (Phase 8.1)
Maintains thread-safe and task-safe active infrastructure environment state,
enforcing strict isolation between DemoMesh simulation and live Kubernetes data.
"""

from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode


# Context variable tracking current active environment per request/task
_active_env_ctx: ContextVar[EnvironmentMode] = ContextVar(
    "active_env_ctx", default=EnvironmentMode.DEMOMESH
)
_active_cluster_id_ctx: ContextVar[Optional[str]] = ContextVar(
    "active_cluster_id_ctx", default=None
)


class EnvironmentContext:
    """Manages active environment mode and enforces isolation boundaries."""

    @classmethod
    def get_current_mode(cls) -> EnvironmentMode:
        """Returns the active environment mode (default: DEMOMESH)."""
        return _active_env_ctx.get()

    @classmethod
    def set_current_mode(cls, mode: EnvironmentMode) -> None:
        """Sets the active environment mode."""
        _active_env_ctx.set(mode)

    @classmethod
    def get_current_cluster_id(cls) -> Optional[str]:
        """Returns current cluster UUID if in KUBERNETES mode."""
        return _active_cluster_id_ctx.get()

    @classmethod
    def set_current_cluster_id(cls, cluster_id: Optional[str]) -> None:
        """Sets current cluster UUID."""
        _active_cluster_id_ctx.set(cluster_id)

    @classmethod
    def get_data_source_tag(cls) -> str:
        """
        Returns mandatory database storage tag ensuring cross-environment isolation:
        - "SIMULATED" for DEMOMESH
        - "LIVE_K8S" for KUBERNETES
        """
        mode = cls.get_current_mode()
        return "LIVE_K8S" if mode == EnvironmentMode.KUBERNETES else "SIMULATED"

    @classmethod
    def is_simulation(cls) -> bool:
        """Returns True if operating within DemoMesh simulation."""
        return cls.get_current_mode() == EnvironmentMode.DEMOMESH

    @classmethod
    def is_live_kubernetes(cls) -> bool:
        """Returns True if operating against live Kubernetes cluster."""
        return cls.get_current_mode() == EnvironmentMode.KUBERNETES

    @classmethod
    @contextmanager
    def scope(cls, mode: EnvironmentMode) -> Generator[None, None, None]:
        """Context manager to temporarily execute within a specific environment mode."""
        prev_token = _active_env_ctx.set(mode)
        try:
            yield
        finally:
            _active_env_ctx.reset(prev_token)


def get_current_environment_mode() -> EnvironmentMode:
    """Helper returning current active environment mode."""
    return EnvironmentContext.get_current_mode()


def get_current_data_source() -> str:
    """Helper returning current active data source tag ('SIMULATED' or 'LIVE_K8S')."""
    return EnvironmentContext.get_data_source_tag()

