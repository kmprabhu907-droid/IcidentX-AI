"""
INCIDENTX AI - Autonomous Workflow API Router (Stage 6.5)
Provides endpoints to trigger, inspect, and approve multi-step reliability self-healing workflows.
"""

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, require_permission, require_roles
from backend.app.core.database import get_db
from backend.app.core.tenant import get_current_tenant
from backend.app.models.organization import Organization
from backend.app.models.user import User, UserRole
from backend.app.models.workflow import WorkflowExecution
from backend.app.schemas.workflow import (
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStepItem,
    WorkflowTriggerRequest,
)
from backend.app.services.workflow.coordinator import workflow_coordinator

router = APIRouter(prefix="/workflows", tags=["Reliability Workflow Engine"])


def _to_workflow_response(wf: WorkflowExecution) -> WorkflowResponse:
    try:
        steps_raw = json.loads(wf.step_history_json) if wf.step_history_json else []
        steps = [
            WorkflowStepItem(
                step=s.get("step", "UNKNOWN"),
                status=s.get("status", "UNKNOWN"),
                timestamp=s.get("timestamp", ""),
                details=s.get("details", {}),
            )
            for s in steps_raw
        ]
    except Exception:
        steps = []

    return WorkflowResponse(
        id=wf.id,
        organization_id=wf.organization_id,
        incident_id=wf.incident_id,
        workflow_type=wf.workflow_type,
        status=wf.status,
        current_step=wf.current_step,
        step_history=steps,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )


@router.post(
    "/trigger",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger an autonomous reliability workflow",
)
async def trigger_workflow(
    payload: WorkflowTriggerRequest,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await workflow_coordinator.start_workflow(
        organization_id=tenant.id,
        incident_id=payload.incident_id,
        service_name=payload.service_name,
        severity=payload.severity,
        title=payload.title,
        auto_approve=payload.auto_approve,
        db=db,
    )
    return _to_workflow_response(execution)


@router.get(
    "",
    response_model=List[WorkflowResponse],
    summary="List reliability workflows for the active tenant",
)
async def list_workflows(
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(WorkflowExecution)
        .where(WorkflowExecution.organization_id == tenant.id)
        .order_by(WorkflowExecution.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [_to_workflow_response(r) for r in records]


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="Inspect workflow execution status and step timeline",
)
async def get_workflow(
    workflow_id: str,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WorkflowExecution).where(
        WorkflowExecution.id == workflow_id,
        WorkflowExecution.organization_id == tenant.id,
    )
    wf = (await db.execute(stmt)).scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return _to_workflow_response(wf)


@router.post(
    "/{workflow_id}/resume",
    response_model=WorkflowResponse,
    summary="Authorize or reject a paused workflow (Human-in-the-Loop Gateway)",
)
async def resume_workflow(
    workflow_id: str,
    payload: WorkflowResumeRequest,
    tenant: Organization = Depends(get_current_tenant),
    current_user: User = Depends(require_permission("remediation:approve")),
    db: AsyncSession = Depends(get_db),
):
    # Verify tenant boundary
    stmt = select(WorkflowExecution).where(
        WorkflowExecution.id == workflow_id,
        WorkflowExecution.organization_id == tenant.id,
    )
    wf = (await db.execute(stmt)).scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    try:
        updated = await workflow_coordinator.resume_workflow(
            workflow_id=workflow_id,
            approved=payload.approved,
            approver=current_user.email,
            comment=payload.comment,
            db=db,
        )
        return _to_workflow_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
