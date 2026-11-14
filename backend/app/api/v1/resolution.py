"""
INCIDENTX AI - Safe Autonomous Incident Resolution REST API (Phase 12)
Provides endpoints for:
- Remediation Plan Generation & Review
- Human & Policy Approval Workflows
- Controlled Execution & Monitoring
- Empirical Recovery Verification
- Automated Rollbacks
- Global Emergency Kill Switch
- Certified Allowlisted Action Library
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException
from backend.app.repositories.incident import IncidentRepository
from backend.app.services.resolution.action_library import action_library, ActionDefinition
from backend.app.services.resolution.kill_switch import kill_switch
from backend.app.services.resolution.resolution_service import resolution_service
from backend.app.services.resolution.schemas import (
    ApprovalStatus,
    KillSwitchState,
    RecoveryVerificationReport,
    ResolutionPlan,
    RollbackExecutionResult,
)

router = APIRouter(tags=["Incident Resolution Engine"])


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalStatus  # APPROVED or REJECTED
    approving_user: str = "SRE-Responder"
    user_role: str = "SRE_LEAD"
    reason: str = "Approved for execution after review"
    emergency_override: bool = False


class KillSwitchToggleRequest(BaseModel):
    is_active: bool
    user: str = "SRE-Operator"
    reason: str = "Manual kill switch toggle"


# ==============================================================================
# Global Governance Endpoints (Module 12.12)
# ==============================================================================

@router.get("/resolution/kill-switch", response_model=KillSwitchState)
async def get_kill_switch_status() -> KillSwitchState:
    """Returns current state of the global remediation kill switch."""
    return await kill_switch.get_state()


@router.post("/resolution/kill-switch", response_model=KillSwitchState)
async def toggle_kill_switch(payload: KillSwitchToggleRequest) -> KillSwitchState:
    """Activates or deactivates the global emergency stop kill switch."""
    if payload.is_active:
        return await kill_switch.activate(user=payload.user, reason=payload.reason)
    else:
        return await kill_switch.deactivate(user=payload.user)


@router.get("/resolution/actions", response_model=List[ActionDefinition])
async def list_action_library() -> List[ActionDefinition]:
    """Lists all allowlisted, certified actions in the remediation library."""
    return action_library.list_actions()


# ==============================================================================
# Incident Resolution Endpoints
# ==============================================================================

@router.post("/incidents/{incident_id}/resolution/plan", response_model=ResolutionPlan)
async def generate_resolution_plan(
    incident_id: str,
    environment: Optional[str] = Query(None, description="Override target environment"),
    target_service: Optional[str] = Query(None, description="Override target service"),
    db: AsyncSession = Depends(get_db),
) -> ResolutionPlan:
    """
    Synthesizes a structured remediation plan using Phase 11 Root Cause findings.
    Enforces risk assessment and anti-tamper approval gating.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    plan = await resolution_service.generate_plan_for_incident(
        incident_id=incident_id,
        session=db,
        environment=environment,
        target_service=target_service,
    )
    return plan


@router.get("/incidents/{incident_id}/resolution/plan", response_model=ResolutionPlan)
async def get_resolution_plan(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResolutionPlan:
    """Retrieves the active resolution plan for the incident."""
    plan = resolution_service.get_plan_for_incident(incident_id)
    if not plan:
        # If not already planned, generate plan on demand
        inc_repo = IncidentRepository(db)
        incident = await inc_repo.get_by_id(incident_id)
        if not incident:
            raise EntityNotFoundException("Incident", incident_id)
        plan = await resolution_service.generate_plan_for_incident(
            incident_id=incident_id,
            session=db,
        )
    return plan


@router.post("/incidents/{incident_id}/resolution/approve", response_model=ResolutionPlan)
async def approve_resolution_plan(
    incident_id: str,
    payload: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> ResolutionPlan:
    """
    Records human SRE approval or rejection for the incident's remediation plan.
    Enforces anti-tamper and role verification invariants.
    """
    try:
        updated_plan = await resolution_service.approve_plan(
            incident_id=incident_id,
            approving_user=payload.approving_user,
            user_role=payload.user_role,
            decision=payload.decision,
            reason=payload.reason,
            session=db,
            emergency_override=payload.emergency_override,
        )
        return updated_plan
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post("/incidents/{incident_id}/resolution/execute", response_model=ResolutionPlan)
async def execute_resolution_plan(
    incident_id: str,
    auto_rollback: bool = Query(True, description="Automatically roll back if verification fails"),
    db: AsyncSession = Depends(get_db),
) -> ResolutionPlan:
    """
    Executes the approved remediation plan, performs recovery verification, and updates lifecycle.
    """
    try:
        updated_plan = await resolution_service.execute_resolution(
            incident_id=incident_id,
            session=db,
            auto_rollback_on_failure=auto_rollback,
        )
        return updated_plan
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.get("/incidents/{incident_id}/resolution/verification", response_model=Optional[RecoveryVerificationReport])
async def get_recovery_verification(
    incident_id: str,
) -> Optional[RecoveryVerificationReport]:
    """Retrieves empirical recovery verification report for the incident."""
    plan = resolution_service.get_plan_for_incident(incident_id)
    if not plan:
        return None
    return plan.recovery_report


@router.get("/incidents/{incident_id}/resolution/rollback", response_model=Optional[RollbackExecutionResult])
async def get_rollback_result(
    incident_id: str,
) -> Optional[RollbackExecutionResult]:
    """Retrieves rollback outcome and state restoration records."""
    plan = resolution_service.get_plan_for_incident(incident_id)
    if not plan:
        return None
    return plan.rollback_result
