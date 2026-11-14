"""
INCIDENTX AI - Infrastructure Environments API Router (Phase 8.1)
Exposes secure endpoints for environment discovery, active context inspection,
role-based environment switching, workload inventory, events, and metrics.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.core.auth import get_optional_current_user
from backend.app.core.tenant import resolve_tenant
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMetadata,
    EnvironmentMode,
    InfrastructureEvent,
    InfrastructureService,
    InfrastructureWorkload,
    ResourceMetric,
    WorkloadStatus,
)
from backend.app.models.user import User

router = APIRouter(prefix="/environments", tags=["Infrastructure Environments"])


class SelectEnvironmentRequest(BaseModel):
    mode: EnvironmentMode = Field(..., description="Target environment mode: 'DEMOMESH' or 'KUBERNETES'")


class EnvironmentSwitchResponse(BaseModel):
    message: str
    previous_mode: str
    active_mode: str
    environment: EnvironmentMetadata


@router.get("", response_model=List[EnvironmentMetadata])
async def list_environments(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Lists all registered infrastructure environments and their live connectivity status."""
    return await environment_manager.list_environments()


@router.get("/active", response_model=EnvironmentMetadata)
async def get_active_environment(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Retrieves metadata and cluster details for the currently active environment."""
    return await environment_manager.get_active_environment_metadata()


@router.post("/select", response_model=EnvironmentSwitchResponse)
async def select_environment(
    payload: SelectEnvironmentRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """
    Selects and activates an infrastructure environment (DemoMesh vs Kubernetes).
    Enforces RBAC authorization: Super Admin, Admin, and SRE Lead only.
    Raises explicit 503 error on connection failure without silent fallback.
    """
    prev_mode = environment_manager.active_mode.value
    meta = await environment_manager.switch_environment(
        target_mode=payload.mode, user=current_user
    )
    return EnvironmentSwitchResponse(
        message=f"Successfully switched infrastructure environment to {payload.mode.value}",
        previous_mode=prev_mode,
        active_mode=payload.mode.value,
        environment=meta,
    )


@router.get("/health", response_model=EnvironmentHealth)
async def get_environment_health(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Inspects live health, responsiveness, and diagnostics for active environment."""
    return await environment_manager.check_health()


@router.get("/services", response_model=List[InfrastructureService])
async def list_environment_services(
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Discovers microservices registered in active environment."""
    return await environment_manager.list_services()


@router.get("/workloads", response_model=List[InfrastructureWorkload])
async def list_environment_workloads(
    namespace: Optional[str] = Query(default=None, description="Optional namespace filter"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Discovers workloads (Pods, Deployments, Containers) in active environment."""
    return await environment_manager.list_workloads(namespace=namespace)


@router.get("/workloads/{workload_id}/status", response_model=Optional[WorkloadStatus])
async def get_workload_status(
    workload_id: str,
    namespace: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Gets granular status, pod health, and restart conditions for a specific workload."""
    status_obj = await environment_manager.get_workload_status(
        workload_id=workload_id, namespace=namespace
    )
    if not status_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workload '{workload_id}' not found in active environment.",
        )
    return status_obj


@router.get("/events", response_model=List[InfrastructureEvent])
async def get_environment_events(
    limit: int = Query(default=50, ge=1, le=200),
    namespace: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Retrieves recent cluster/mesh warning and normal events."""
    return await environment_manager.get_events(limit=limit, namespace=namespace)


@router.get("/metrics", response_model=List[ResourceMetric])
async def get_environment_metrics(
    workload_id: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    tenant_org_id: str = Depends(resolve_tenant),
):
    """Fetches real-time CPU, memory, and performance metrics tagged with environment data source."""
    return await environment_manager.get_metrics(workload_id=workload_id)
