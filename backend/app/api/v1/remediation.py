"""
INCIDENTX AI - Remediation API Router
Provides REST endpoints for Remediation Recommendations, Approvals, Registry inspection,
Execution in simulation, Verification reports, and Emergency Stop controls.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException
from backend.app.models.incident import Incident
from backend.app.models.remediation import RemediationAction, RemediationPolicy
from backend.app.schemas.remediation import (
    ActionRegistryItemResponse,
    ApproveActionRequest,
    EmergencyStopRequest,
    RejectActionRequest,
    RemediationActionResponse,
    RemediationPolicyResponse,
    RemediationPolicyUpdate,
)
from backend.app.services.remediation.engine import remediation_intelligence_engine
from backend.app.services.remediation.executor import remediation_executor
from backend.app.services.remediation.registry import remediation_registry
from backend.app.services.remediation.safety import safety_engine
from backend.app.services.remediation.verification import TelemetryVerifier

router = APIRouter(tags=["Remediation & Self-Healing Engine"])


# ============================================================================
# Action Registry & Policy Endpoints
# ============================================================================

@router.get("/remediation/registry", response_model=List[ActionRegistryItemResponse])
async def get_action_registry():
    """Retrieve catalog of all predefined, safe remediation actions and parameter schemas."""
    return remediation_registry.list_actions()


@router.get("/remediation/policy", response_model=RemediationPolicyResponse)
async def get_remediation_policy(db: AsyncSession = Depends(get_db)):
    """Retrieve current global safety policy, execution mode, and circuit breaker state."""
    policy = await safety_engine.get_or_create_policy(db)
    return RemediationPolicyResponse.model_validate(policy)


@router.put("/remediation/policy", response_model=RemediationPolicyResponse)
async def update_remediation_policy(
    payload: RemediationPolicyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update safety execution mode (RECOMMENDATION_ONLY, HUMAN_APPROVAL, CONTROLLED_AUTONOMOUS),
    autonomous allowlist, and execution budget.
    """
    policy = await safety_engine.update_policy(
        session=db,
        mode=payload.mode,
        is_autonomous_enabled=payload.is_autonomous_enabled,
        allowlisted_action_ids=payload.allowlisted_action_ids,
        max_actions_per_incident=payload.max_actions_per_incident,
    )
    return RemediationPolicyResponse.model_validate(policy)


@router.post("/remediation/emergency-stop", response_model=RemediationPolicyResponse)
async def trigger_emergency_stop(
    payload: EmergencyStopRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    EMERGENCY STOP: Immediately locks down all remediation execution and trips the circuit breaker.
    Reverts execution mode to RECOMMENDATION_ONLY.
    """
    policy = await safety_engine.trigger_emergency_stop(session=db, reason=payload.reason)
    return RemediationPolicyResponse.model_validate(policy)


@router.post("/remediation/reset-circuit-breaker", response_model=RemediationPolicyResponse)
async def reset_circuit_breaker(db: AsyncSession = Depends(get_db)):
    """Reset a tripped circuit breaker after human operator verification."""
    policy = await safety_engine.reset_circuit_breaker(session=db)
    return RemediationPolicyResponse.model_validate(policy)


# ============================================================================
# Incident-Specific Remediation Endpoints
# ============================================================================

@router.get("/incidents/{incident_id}/remediation/recommendations")
async def get_incident_remediation_recommendations(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Synthesize and retrieve ranked recovery recommendations for an investigated incident.
    Grounds recommendations in empirical evidence and identifies contraindications.
    """
    inc_stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(inc_stmt)
    incident = inc_res.scalar_one_or_none()
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    actions = await remediation_intelligence_engine.generate_recommendations(incident_id, db)
    return {
        "incident_id": incident_id,
        "total_recommendations": len(actions),
        "actions": [RemediationActionResponse.model_validate(a).model_dump() for a in actions],
        "disclaimer": "A recommendation is never treated as proof that the root cause is correct.",
    }


@router.post("/incidents/{incident_id}/remediation/recommend")
async def trigger_remediation_recommendations(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Explicitly trigger the intelligence engine to formulate recovery actions."""
    inc_stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(inc_stmt)
    incident = inc_res.scalar_one_or_none()
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    actions = await remediation_intelligence_engine.generate_recommendations(incident_id, db)
    return {
        "incident_id": incident_id,
        "generated_count": len(actions),
        "actions": [RemediationActionResponse.model_validate(a).model_dump() for a in actions],
    }


@router.get("/incidents/{incident_id}/remediation/actions", response_model=List[RemediationActionResponse])
async def list_incident_remediation_actions(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all proposed, approved, executed, and verified remediation actions for an incident."""
    inc_stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(inc_stmt)
    incident = inc_res.scalar_one_or_none()
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    stmt = select(RemediationAction).where(RemediationAction.incident_id == incident_id).order_by(desc(RemediationAction.expected_benefit))
    res = await db.execute(stmt)
    actions = list(res.scalars().all())
    return [RemediationActionResponse.model_validate(a) for a in actions]


@router.post("/incidents/{incident_id}/remediation/actions/{action_id}/approve", response_model=RemediationActionResponse)
async def approve_remediation_action(
    incident_id: str,
    action_id: str,
    payload: ApproveActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Approve a remediation action with human operator signature."""
    stmt = select(RemediationAction).where(
        RemediationAction.id == action_id,
        RemediationAction.incident_id == incident_id
    )
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise EntityNotFoundException("RemediationAction", action_id)

    action.approval_status = "APPROVED"
    action.approved_by = payload.approved_by
    action.approved_at = datetime.now(timezone.utc)
    action.approval_comment = payload.comment
    action.status = "APPROVED"
    await db.flush()

    return RemediationActionResponse.model_validate(action)


@router.post("/incidents/{incident_id}/remediation/actions/{action_id}/reject", response_model=RemediationActionResponse)
async def reject_remediation_action(
    incident_id: str,
    action_id: str,
    payload: RejectActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reject a proposed remediation action."""
    stmt = select(RemediationAction).where(
        RemediationAction.id == action_id,
        RemediationAction.incident_id == incident_id
    )
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise EntityNotFoundException("RemediationAction", action_id)

    action.approval_status = "REJECTED"
    action.status = "REJECTED"
    action.approved_by = payload.rejected_by
    action.approval_comment = payload.reason
    await db.flush()

    return RemediationActionResponse.model_validate(action)


@router.post("/incidents/{incident_id}/remediation/actions/{action_id}/execute", response_model=RemediationActionResponse)
async def execute_remediation_action(
    incident_id: str,
    action_id: str,
    is_autonomous: bool = Query(default=False),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a remediation action inside the isolated simulation environment.
    Enforces mode safety, approval requirements, parameter validation, and post-action verification.
    """
    action = await remediation_executor.execute_action(
        action_db_id=action_id,
        session=db,
        is_autonomous_trigger=is_autonomous,
    )
    return RemediationActionResponse.model_validate(action)


@router.post("/incidents/{incident_id}/remediation/actions/{action_id}/rollback", response_model=RemediationActionResponse)
async def rollback_remediation_action(
    incident_id: str,
    action_id: str,
    operator: str = Query(default="operator"),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger rollback for an executed remediation action."""
    action = await remediation_executor.rollback_action(
        action_db_id=action_id,
        session=db,
        requested_by=operator,
    )
    return RemediationActionResponse.model_validate(action)


@router.get("/incidents/{incident_id}/remediation/actions/{action_id}/verification")
async def get_action_verification_report(
    incident_id: str,
    action_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed before vs after telemetry comparison and empirical recovery verification."""
    stmt = select(RemediationAction).where(
        RemediationAction.id == action_id,
        RemediationAction.incident_id == incident_id
    )
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise EntityNotFoundException("RemediationAction", action_id)

    report = TelemetryVerifier.compare_snapshots(
        service_name=action.target_service_name,
        before_snapshot_json=action.snapshot_before,
        after_snapshot_json=action.snapshot_after,
    )
    return {
        "action_id": action.id,
        "action_name": action.name,
        "target_service": action.target_service_name,
        "execution_status": action.status,
        "verification_status": action.verification_status,
        "verification_report": report,
        "raw_verification_details": json.loads(action.verification_details) if action.verification_details else None,
    }
