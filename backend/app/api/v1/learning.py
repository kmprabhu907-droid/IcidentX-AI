"""
INCIDENTX AI - Recovery Verification & Self-Learning API Endpoints (Phase 13)
Exposes recovery verification, telemetry diffing, stability monitoring,
automated postmortems, historical knowledge, and self-learning policy controls.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.app.core.logging import logger
from backend.app.services.learning.learning_service import learning_service
from backend.app.services.learning.schemas import (
    AdvancedRecoveryReport,
    ContinuousImprovementRecommendation,
    FailurePattern,
    HumanFeedback,
    LearningPolicyChange,
    PostmortemReport,
    RecoveryCriteria,
    RecoveryStabilityReport,
    SimilarIncidentMatch,
    TelemetryComparisonReport,
    TelemetrySnapshot,
    TelemetryStage,
)

router = APIRouter(prefix="", tags=["Recovery & Self-Learning (Phase 13)"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class RecoveryVerifyRequest(BaseModel):
    service_name: str
    environment: str = "DEMOMESH"
    custom_criteria: Optional[RecoveryCriteria] = None


class StabilityCheckRequest(BaseModel):
    service_name: str
    observation_window_seconds: int = 300
    simulate_regression: bool = False


class GeneratePostmortemRequest(BaseModel):
    title: str
    severity: str = "SEV-1"
    environment: str = "DEMOMESH"
    affected_services: List[str]
    detected_at: Optional[datetime] = None
    verified_root_cause: str
    root_cause_is_conclusive: bool = True
    remediation_performed: str = "Rollback and rolling restart"
    customer_impact_summary: Optional[str] = None


class PolicyRollbackRequest(BaseModel):
    target_version_id: str
    rolled_back_by: str = "oncall-lead"


class SubmitFeedbackRequest(BaseModel):
    reviewer: str = "oncall-engineer"
    rating: int = 5
    comments: str = ""
    corrected_root_cause: Optional[str] = None


class TelemetrySnapshotRequest(BaseModel):
    service_name: str
    stage: TelemetryStage
    environment: str = "DEMOMESH"
    replicas_desired: int = 2
    replicas_ready: int = 2
    restart_count: int = 0
    error_rate_percent: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    throughput_rps: Optional[float] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    db_query_latency_ms: Optional[float] = None
    dependency_failure_rate_percent: Optional[float] = None


# ============================================================================
# MODULE 13.1 & 13.2 — RECOVERY VERIFICATION & TELEMETRY COMPARISON
# ============================================================================

@router.post(
    "/incidents/{incident_id}/recovery/snapshot",
    response_model=TelemetrySnapshot,
    summary="Record a point-in-time telemetry snapshot",
)
async def record_snapshot(incident_id: str, payload: TelemetrySnapshotRequest):
    """Records a baseline or post-remediation telemetry snapshot."""
    import uuid
    snapshot = TelemetrySnapshot(
        snapshot_id=f"snap-{uuid.uuid4().hex[:10]}",
        incident_id=incident_id,
        service_name=payload.service_name,
        environment=payload.environment,
        stage=payload.stage,
        replicas_desired=payload.replicas_desired,
        replicas_ready=payload.replicas_ready,
        restart_count=payload.restart_count,
        pod_readiness_ratio=round(payload.replicas_ready / max(1, payload.replicas_desired), 2),
        error_rate_percent=payload.error_rate_percent,
        p95_latency_ms=payload.p95_latency_ms,
        p99_latency_ms=payload.p99_latency_ms,
        throughput_rps=payload.throughput_rps,
        cpu_percent=payload.cpu_percent,
        memory_percent=payload.memory_percent,
        db_query_latency_ms=payload.db_query_latency_ms,
        dependency_failure_rate_percent=payload.dependency_failure_rate_percent,
    )
    learning_service.record_snapshot(snapshot)
    return snapshot


@router.post(
    "/incidents/{incident_id}/recovery/verify",
    response_model=AdvancedRecoveryReport,
    summary="Run advanced empirical recovery verification",
)
async def verify_recovery(incident_id: str, payload: RecoveryVerifyRequest):
    """Executes multi-pillar recovery verification for an incident."""
    report = await learning_service.verify_recovery(
        incident_id=incident_id,
        service_name=payload.service_name,
        custom_criteria=payload.custom_criteria,
        environment=payload.environment,
    )
    return report


@router.get(
    "/incidents/{incident_id}/recovery/verification",
    response_model=AdvancedRecoveryReport,
    summary="Get latest recovery verification report",
)
async def get_recovery_verification(incident_id: str):
    report = learning_service.get_verification(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recovery verification found for incident {incident_id}.",
        )
    return report


@router.get(
    "/incidents/{incident_id}/telemetry-comparison",
    response_model=TelemetryComparisonReport,
    summary="Get before-and-after telemetry comparison",
)
async def get_telemetry_comparison(incident_id: str):
    comp = learning_service.get_telemetry_comparison(incident_id)
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry comparison found for incident {incident_id}. Run recovery verification first.",
        )
    return comp


# ============================================================================
# MODULE 13.3 — RECOVERY STABILITY MONITOR
# ============================================================================

@router.post(
    "/incidents/{incident_id}/stability/check",
    response_model=RecoveryStabilityReport,
    summary="Evaluate multi-interval recovery stability",
)
async def check_stability(incident_id: str, payload: StabilityCheckRequest):
    report = learning_service.check_stability(
        incident_id=incident_id,
        service_name=payload.service_name,
        observation_window_seconds=payload.observation_window_seconds,
        simulate_regression=payload.simulate_regression,
    )
    return report


@router.get(
    "/incidents/{incident_id}/stability",
    response_model=RecoveryStabilityReport,
    summary="Get latest recovery stability report",
)
async def get_stability(incident_id: str):
    report = learning_service.get_stability(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stability report found for incident {incident_id}.",
        )
    return report


# ============================================================================
# MODULE 13.4 — AUTOMATED POSTMORTEM GENERATION
# ============================================================================

@router.post(
    "/incidents/{incident_id}/postmortem",
    response_model=PostmortemReport,
    summary="Generate enterprise incident postmortem",
)
async def generate_postmortem(incident_id: str, payload: GeneratePostmortemRequest):
    detected_at = payload.detected_at or datetime.now(timezone.utc)
    report = learning_service.generate_postmortem(
        incident_id=incident_id,
        title=payload.title,
        severity=payload.severity,
        environment=payload.environment,
        affected_services=payload.affected_services,
        detected_at=detected_at,
        verified_root_cause=payload.verified_root_cause,
        root_cause_is_conclusive=payload.root_cause_is_conclusive,
        remediation_performed=payload.remediation_performed,
        customer_impact_summary=payload.customer_impact_summary or "Internal simulated degradation. 0 external users affected.",
    )
    return report


@router.get(
    "/incidents/{incident_id}/postmortem",
    response_model=PostmortemReport,
    summary="Get generated postmortem",
)
async def get_postmortem(incident_id: str):
    report = learning_service.get_postmortem(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No postmortem found for incident {incident_id}.",
        )
    return report


@router.get(
    "/incidents/{incident_id}/postmortem/html",
    response_class=HTMLResponse,
    summary="Get postmortem formatted in print-ready HTML",
)
async def get_postmortem_html(incident_id: str):
    report = learning_service.get_postmortem(incident_id)
    if not report or not report.html_content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No HTML postmortem found for incident {incident_id}.",
        )
    return HTMLResponse(content=report.html_content)


# ============================================================================
# MODULE 13.5 — INCIDENT KNOWLEDGE ENGINE
# ============================================================================

@router.get(
    "/learning/knowledge/search",
    response_model=List[SimilarIncidentMatch],
    summary="Search historical incident knowledge base",
)
async def search_knowledge(
    service: Optional[str] = Query(None, description="Service name"),
    error: Optional[str] = Query(None, description="Error signature"),
    query: Optional[str] = Query(None, description="Free text keywords"),
):
    matches = learning_service.search_knowledge(
        service_name=service,
        error_signature=error,
        query=query,
    )
    return matches


@router.get(
    "/learning/patterns",
    response_model=List[FailurePattern],
    summary="Get recurring failure patterns",
)
async def get_recurring_patterns():
    return learning_service.get_recurring_patterns()


# ============================================================================
# MODULE 13.6 — CONTROLLED SELF-LEARNING
# ============================================================================

@router.get(
    "/learning/policy",
    response_model=Dict[str, Any],
    summary="Get active and historical learning policies",
)
async def get_learning_policy():
    active = learning_service.learner.get_active_policy()
    all_versions = learning_service.learner.list_policy_versions()
    return {
        "active_policy": active,
        "history": all_versions,
        "total_versions": len(all_versions),
    }


@router.post(
    "/learning/policy/rollback",
    summary="Roll back learning policy to an earlier version",
)
async def rollback_policy(payload: PolicyRollbackRequest):
    success = learning_service.learner.rollback_to_version(
        target_version_id=payload.target_version_id,
        rolled_back_by=payload.rolled_back_by,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy version {payload.target_version_id} not found.",
        )
    return {
        "status": "ROLLED_BACK",
        "active_version": payload.target_version_id,
        "rolled_back_by": payload.rolled_back_by,
    }


@router.post(
    "/incidents/{incident_id}/feedback",
    response_model=HumanFeedback,
    summary="Submit human SRE feedback for controlled learning",
)
async def submit_human_feedback(incident_id: str, payload: SubmitFeedbackRequest):
    feedback = learning_service.submit_human_feedback(
        incident_id=incident_id,
        reviewer=payload.reviewer,
        rating=payload.rating,
        comments=payload.comments,
        corrected_root_cause=payload.corrected_root_cause,
    )
    return feedback


# ============================================================================
# MODULE 13.7 — CONTINUOUS IMPROVEMENT RECOMMENDATIONS
# ============================================================================

@router.get(
    "/incidents/{incident_id}/recommendations",
    response_model=List[ContinuousImprovementRecommendation],
    summary="Get continuous improvement recommendations",
)
async def get_recommendations(incident_id: str):
    return learning_service.get_recommendations(incident_id)
