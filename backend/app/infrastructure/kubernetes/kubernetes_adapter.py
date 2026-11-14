"""
INCIDENTX AI - Kubernetes Infrastructure Adapter (Phase 8.1)
Concrete implementation of BaseInfrastructureAdapter for live Kubernetes clusters.
Enforces strictly read-only observability operations and least-privilege RBAC.
"""

from datetime import datetime, timezone
import time
from typing import List, Optional
from backend.app.core.logging import logger
from backend.app.infrastructure.core.base_adapter import BaseInfrastructureAdapter
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
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient
from backend.app.infrastructure.kubernetes.kubernetes_events import KubernetesEvents
from backend.app.infrastructure.kubernetes.kubernetes_health import KubernetesHealth
from backend.app.infrastructure.kubernetes.kubernetes_inventory import KubernetesInventory


class KubernetesAdapter(BaseInfrastructureAdapter):
    """Infrastructure Adapter for Live Kubernetes Clusters (Read-Only)."""

    def __init__(self, cluster_id: str = "k8s-default", client: Optional[KubernetesClient] = None):
        self.cluster_id = cluster_id
        self.client = client or KubernetesClient(cluster_id=cluster_id)
        self.inventory = KubernetesInventory(self.client)
        self.health = KubernetesHealth(self.client)
        self.events = KubernetesEvents(self.client)
        self._connected: bool = False
        self._last_sync: str = datetime.now(timezone.utc).isoformat()
        self._connection_error: Optional[str] = None
        self._cached_version: str = "unknown"

    @property
    def mode(self) -> EnvironmentMode:
        return EnvironmentMode.KUBERNETES

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_read_only(self) -> bool:
        return True

    @property
    def data_source(self) -> str:
        return "LIVE_K8S"

    async def connect(self) -> bool:
        from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
            kubernetes_connection_manager,
        )
        if self.client._mock_handler:
            try:
                ver = await self.client.get_version()
                self._cached_version = ver.get("gitVersion", "v1.30.2-mock")
                self._connected = True
                self._connection_error = None
                self._last_sync = datetime.now(timezone.utc).isoformat()
                return True
            except Exception as e:
                self._connected = False
                self._connection_error = str(e)
                return False

        try:
            success = await kubernetes_connection_manager.connect()
            if success:
                self._connected = True
                self._connection_error = None
                self._last_sync = datetime.now(timezone.utc).isoformat()
                self._cached_version = kubernetes_connection_manager._discovered_version
                return True
            else:
                self._connected = False
                self._connection_error = kubernetes_connection_manager._last_error
                return False
        except Exception as e:
            self._connected = False
            self._connection_error = str(e)
            return False

    async def disconnect(self) -> None:
        from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
            kubernetes_connection_manager,
        )
        self._connected = False
        await kubernetes_connection_manager.disconnect()
        logger.info(f"[KubernetesAdapter] Disconnected from cluster '{self.cluster_id}'")

    async def health_check(self) -> EnvironmentHealth:
        return await self.health.evaluate_health()

    async def list_nodes(self):
        return await self.inventory.list_nodes()

    async def list_namespaces_detailed(self):
        return await self.inventory.list_namespaces()

    async def list_pods_detailed(self, namespace: Optional[str] = None):
        return await self.inventory.list_pods_detailed(namespace=namespace)

    async def list_deployments_detailed(self, namespace: Optional[str] = None):
        return await self.inventory.list_deployments_detailed(namespace=namespace)

    async def list_services_detailed(self, namespace: Optional[str] = None):
        return await self.inventory.list_services_detailed(namespace=namespace)

    async def get_cluster_overview(self):
        return await self.inventory.get_cluster_overview()

    async def get_kubernetes_resource_metrics(self, workload_id: Optional[str] = None, namespace: Optional[str] = None):
        return await self.inventory.get_resource_metrics(workload_id=workload_id, namespace=namespace)

    async def list_services(self) -> List[InfrastructureService]:
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return await self.inventory.list_services()

    async def list_workloads(self, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return await self.inventory.list_workloads(namespace=namespace)

    async def get_workload_status(
        self, workload_id: str, namespace: Optional[str] = None
    ) -> Optional[WorkloadStatus]:
        return await self.inventory.get_workload_status(workload_id=workload_id, namespace=namespace)

    async def get_events(
        self, limit: int = 50, namespace: Optional[str] = None
    ) -> List[InfrastructureEvent]:
        return await self.events.list_events(namespace=namespace, limit=limit)

    async def get_resource_metrics(
        self, workload_id: Optional[str] = None
    ) -> List[ResourceMetric]:
        """
        Discovers resource requests and limits from live workloads,
        tagged with data_source = 'LIVE_K8S' to prevent cross-environment pollution.
        """
        workloads = await self.list_workloads()
        metrics_list: List[ResourceMetric] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for wl in workloads:
            if workload_id and workload_id not in [wl.id, wl.name]:
                continue

            metrics_list.append(
                ResourceMetric(
                    workload_id=wl.id,
                    workload_name=wl.name,
                    namespace=wl.namespace,
                    metric_name="cpu_cores_request",
                    value=wl.cpu_request_cores,
                    unit="cores",
                    timestamp=now_iso,
                    data_source="LIVE_K8S",
                )
            )
            metrics_list.append(
                ResourceMetric(
                    workload_id=wl.id,
                    workload_name=wl.name,
                    namespace=wl.namespace,
                    metric_name="memory_mb_request",
                    value=wl.memory_request_mb,
                    unit="mb",
                    timestamp=now_iso,
                    data_source="LIVE_K8S",
                )
            )
            metrics_list.append(
                ResourceMetric(
                    workload_id=wl.id,
                    workload_name=wl.name,
                    namespace=wl.namespace,
                    metric_name="restart_count",
                    value=float(wl.restart_count),
                    unit="count",
                    timestamp=now_iso,
                    data_source="LIVE_K8S",
                )
            )

        return metrics_list

    async def get_environment_metadata(self) -> EnvironmentMetadata:
        namespaces = []
        services_count = 0
        workloads_count = 0

        if self._connected:
            try:
                namespaces = await self.client.list_namespaces()
                svcs = await self.inventory.list_services()
                wls = await self.inventory.list_workloads()
                services_count = len(svcs)
                workloads_count = len(wls)
            except Exception:
                pass

        creds = self.client._resolve_credentials()
        endpoint = creds.api_server_url if creds else "k8s://unconfigured"

        return EnvironmentMetadata(
            mode=EnvironmentMode.KUBERNETES,
            name=f"Kubernetes Cluster ({self.cluster_id})",
            cluster_name=self.cluster_id,
            cluster_version=self._cached_version,
            api_endpoint=endpoint,
            version=self._cached_version,
            connection_status=ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.ERROR,
            is_read_only=True,
            is_simulated=False,
            data_source="LIVE_K8S",
            namespaces=namespaces,
            namespace="default",
            node_count=len(namespaces) or 1,
            total_services=services_count,
            total_workloads=workloads_count,
            last_sync_timestamp=self._last_sync,
            connection_error=self._connection_error,
        )
