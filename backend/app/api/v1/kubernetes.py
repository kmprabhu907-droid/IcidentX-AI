"""
INCIDENTX AI - Kubernetes Integration API Router (Phase 8.2)
Exposes read-only REST endpoints for cluster connection status, node topologies,
namespaces, pods, deployments, services, deduplicated events, and resource metrics.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.core.auth import get_optional_current_user
from backend.app.core.tenant import resolve_tenant
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMode,
    InfrastructureEvent,
    KubernetesClusterOverview,
    KubernetesConnectionDetails,
    KubernetesDeployment,
    KubernetesNamespace,
    KubernetesNode,
    KubernetesPod,
    KubernetesResourceMetrics,
    KubernetesService,
)
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter
from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
    kubernetes_connection_manager,
)
from backend.app.models.user import User

router = APIRouter(prefix="/kubernetes", tags=["Kubernetes Cluster Integration"])


def _get_kubernetes_adapter() -> KubernetesAdapter:
    adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    if not isinstance(adapter, KubernetesAdapter):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kubernetes adapter is not configured in environment registry.",
        )
    return adapter


@router.get("/connection", response_model=KubernetesConnectionDetails)
async def get_connection_details(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Returns safe, masked cluster connection configuration and live discovery status."""
    return kubernetes_connection_manager.get_connection_details()


@router.get("/cluster", response_model=KubernetesClusterOverview)
async def get_cluster_overview(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Returns consolidated cluster metadata, healthy workload ratios, and metrics server state."""
    adapter = _get_kubernetes_adapter()
    return await adapter.get_cluster_overview()


@router.get("/health", response_model=EnvironmentHealth)
async def get_kubernetes_health(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Probes control plane version, API responsiveness, and namespace accessibility."""
    adapter = _get_kubernetes_adapter()
    return await adapter.health_check()


@router.get("/nodes", response_model=List[KubernetesNode])
async def list_cluster_nodes(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Discovers physical or virtual nodes, readiness states, conditions, and allocatable capacity."""
    adapter = _get_kubernetes_adapter()
    return await adapter.list_nodes()


@router.get("/namespaces", response_model=List[KubernetesNamespace])
async def list_cluster_namespaces(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Discovers namespaces with associated workload counts and lifecycle phase."""
    adapter = _get_kubernetes_adapter()
    return await adapter.list_namespaces_detailed()


@router.get("/pods", response_model=List[KubernetesPod])
async def list_cluster_pods(
    namespace: Optional[str] = Query(default=None, description="Optional namespace filter"),
    phase: Optional[str] = Query(default=None, description="Filter by pod phase (Running, Pending, Failed)"),
    search: Optional[str] = Query(default=None, description="Search by pod name substring"),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Inspects live pods with container restart counts, IP addresses, and node placement."""
    adapter = _get_kubernetes_adapter()
    pods = await adapter.list_pods_detailed(namespace=namespace)

    if phase:
        pods = [p for p in pods if p.phase.lower() == phase.lower()]
    if search:
        s_lower = search.lower()
        pods = [p for p in pods if s_lower in p.name.lower()]

    return pods[:limit]


@router.get("/deployments", response_model=List[KubernetesDeployment])
async def list_cluster_deployments(
    namespace: Optional[str] = Query(default=None, description="Optional namespace filter"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Inspects deployments, desired vs available replicas, and rollout health conditions."""
    adapter = _get_kubernetes_adapter()
    return await adapter.list_deployments_detailed(namespace=namespace)


@router.get("/services", response_model=List[KubernetesService])
async def list_cluster_services(
    namespace: Optional[str] = Query(default=None, description="Optional namespace filter"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Inspects Kubernetes services, port mappings, cluster IPs, and endpoint availability."""
    adapter = _get_kubernetes_adapter()
    return await adapter.list_services_detailed(namespace=namespace)


@router.get("/events", response_model=List[InfrastructureEvent])
async def list_cluster_events(
    namespace: Optional[str] = Query(default=None),
    only_warnings: bool = Query(default=False, description="Filter only warning and critical events"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Retrieves deduplicated live cluster events, classifying failure signatures."""
    adapter = _get_kubernetes_adapter()
    return await adapter.events.list_events(namespace=namespace, limit=limit, only_warnings=only_warnings)


@router.get("/metrics", response_model=List[KubernetesResourceMetrics])
async def get_cluster_resource_metrics(
    workload_id: Optional[str] = Query(default=None, description="Filter metrics for a specific pod"),
    namespace: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """
    Inspects configured CPU/Memory requests and limits vs live measured utilization.
    Explicitly reports null measured fields if Metrics Server is not installed.
    """
    adapter = _get_kubernetes_adapter()
    return await adapter.get_kubernetes_resource_metrics(workload_id=workload_id, namespace=namespace)
