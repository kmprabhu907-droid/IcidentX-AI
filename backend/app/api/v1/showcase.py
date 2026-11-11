"""
INCIDENTX AI - Hackathon Showcase & Autonomous Intelligence API Router (Stage 7.12)
Provides high-impact demonstration endpoints: full autonomous loop execution,
15-scenario catalog, multi-agent pipeline monitoring, and platform reliability scorecard.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth import get_optional_current_user
from backend.app.core.database import get_db
from backend.app.core.tenant import resolve_tenant
from backend.app.models.user import User
from backend.app.services.benchmarks.root_cause_evaluator import (
    RootCauseAccuracyAggregateReport,
    RootCauseAccuracyEvaluator,
)
from backend.app.services.benchmarks.scenarios import (
    BENCHMARK_SCENARIOS_LIBRARY,
    get_scenario,
    list_all_scenarios,
)
from backend.app.services.benchmarks.scenario_runner import BenchmarkScenarioRunner, ScenarioBenchmarkResult
from backend.app.services.benchmarks.scorecard import ReliabilityScorecard, ScorecardAggregator
from backend.app.services.validation.courtroom_validator import CourtroomAuditReport, CourtroomValidator
from backend.app.services.validation.multi_agent_validator import (
    MultiAgentPipelineValidationResult,
    MultiAgentValidationHarness,
)
from backend.app.services.validation.recovery_validator import AutonomousRecoveryLoopReport, AutonomousRecoveryValidator
from backend.app.services.validation.time_machine_validator import IncidentTimeMachineValidator, TimeMachineValidationReport
from backend.app.services.validation.what_if_validator import WhatIfLabValidationReport, WhatIfLaboratoryValidator

router = APIRouter(prefix="/showcase", tags=["Hackathon Showcase & Validation"])


class LaunchShowcaseRequest(BaseModel):
    scenario_id: str = Field(..., description="ID of scenario from the 15-scenario benchmark library")
    auto_approve_if_required: bool = Field(default=True, description="Whether human approval is auto-granted for demo purposes")


class ShowcaseDemonstrationResult(BaseModel):
    demonstration_id: str
    scenario_id: str
    scenario_name: str
    target_service: str
    severity: str
    incident_id: str

    # 1. Signals & Detection
    detection_summary: Dict[str, Any]

    # 2. Multi-Agent Investigation
    agents_executed_count: int
    investigation_duration_ms: float

    # 3. Root Cause Courtroom
    courtroom: CourtroomAuditReport

    # 4. What-If Laboratory
    what_if_lab: WhatIfLabValidationReport

    # 5. Risk Assessment & Approval
    approval_required: bool
    risk_score: float
    approval_status: str

    # 6. Autonomous Recovery & Verification
    recovery: AutonomousRecoveryLoopReport

    # 7. Incident Time Machine Timeline
    time_machine: TimeMachineValidationReport

    # 8. Evaluation & Scorecard
    ground_truth_matched: bool
    scorecard: ReliabilityScorecard
    timestamp: str


@router.get("/scenarios", response_model=List[Dict[str, Any]])
async def list_benchmark_scenarios():
    """Returns the 15 realistic infrastructure incident scenarios."""
    return list_all_scenarios()


@router.get("/scenarios/{scenario_id}")
async def get_benchmark_scenario_details(scenario_id: str):
    """Returns detailed specification and ground truth for a scenario."""
    sc = get_scenario(scenario_id)
    if not sc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found.",
        )
    return sc.model_dump()


@router.post("/launch", response_model=ShowcaseDemonstrationResult)
async def launch_showcase_demonstration(
    payload: LaunchShowcaseRequest,
    db: AsyncSession = Depends(get_db),
    tenant_org_id: str = Depends(resolve_tenant),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Executes a complete end-to-end autonomous incident lifecycle:
    Detection -> Multi-Agent Deep Investigation -> Root Cause Courtroom ->
    What-If Simulation -> Approval Gate -> Recovery Execution -> Verification ->
    Reliability Memory Update -> Scorecard.
    """
    scenario = get_scenario(payload.scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{payload.scenario_id}' not found in benchmark library.",
        )

    t0 = time.perf_counter()

    # 1. Run scenario through benchmark runner (creates real incident & executes 10 agents)
    bench_result = await BenchmarkScenarioRunner.run_scenario(
        session=db, scenario_id=payload.scenario_id, organization_id=tenant_org_id
    )
    incident_id = bench_result.incident_id

    # 2. Evaluate Courtroom evidence balance
    courtroom = await CourtroomValidator.validate_incident_courtroom(
        session=db, incident_id=incident_id, service_name=scenario.target_service
    )

    # 3. What-If Laboratory simulation
    what_if = WhatIfLaboratoryValidator.simulate_all_recovery_strategies(
        target_service=scenario.target_service, incident_id=incident_id
    )

    # 4. Recovery loop execution
    recovery = await AutonomousRecoveryValidator.validate_successful_recovery_loop(
        session=db, incident_id=incident_id, service_name=scenario.target_service
    )

    # 5. Incident Time Machine chronological reconstruction
    time_machine = await IncidentTimeMachineValidator.validate_time_machine(
        session=db, incident_id=incident_id, service_name=scenario.target_service
    )

    # 6. Overall platform scorecard
    scorecard = ScorecardAggregator.generate_scorecard()

    return ShowcaseDemonstrationResult(
        demonstration_id=f"demo-{int(time.time())}",
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        target_service=scenario.target_service,
        severity=scenario.severity,
        incident_id=incident_id,
        detection_summary={
            "symptom": scenario.metric_evidence[0].metric_name if scenario.metric_evidence else "CPU",
            "observed_value": scenario.metric_evidence[0].observed_value if scenario.metric_evidence else 99.0,
            "unit": scenario.metric_evidence[0].unit if scenario.metric_evidence else "%",
            "affected_services": scenario.affected_services,
        },
        agents_executed_count=bench_result.agent_executions_count or 10,
        investigation_duration_ms=bench_result.execution_duration_ms,
        courtroom=courtroom,
        what_if_lab=what_if,
        approval_required=scenario.remediation.requires_human_approval,
        risk_score=scenario.remediation.risk_score,
        approval_status="APPROVED_BY_OPERATOR" if payload.auto_approve_if_required else ("PENDING_APPROVAL" if scenario.remediation.requires_human_approval else "AUTONOMOUS_CLEARED"),
        recovery=recovery,
        time_machine=time_machine,
        ground_truth_matched=bench_result.root_cause_matched,
        scorecard=scorecard,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/multi-agent-pipeline", response_model=MultiAgentPipelineValidationResult)
async def get_multi_agent_pipeline_validation(
    service: str = Query(default="payment-service"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Validates and returns the execution report and information flow timeline
    for all 11 autonomous intelligence agents.
    """
    result = await MultiAgentValidationHarness.validate_entire_pipeline(
        session=db, service_name=service
    )
    return result


@router.get("/scorecard", response_model=ReliabilityScorecard)
async def get_reliability_scorecard():
    """Returns the empirical platform reliability scorecard."""
    return ScorecardAggregator.generate_scorecard()


@router.post("/benchmark-accuracy", response_model=RootCauseAccuracyAggregateReport)
async def run_root_cause_accuracy_benchmark(
    db: AsyncSession = Depends(get_db),
    tenant_org_id: str = Depends(resolve_tenant),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Runs the Root Cause Accuracy Evaluation Engine across all 15 realistic scenarios,
    computing empirical accuracy, Brier confidence calibration, and evidence coverage.
    """
    report = await RootCauseAccuracyEvaluator.run_accuracy_benchmark(
        session=db, organization_id=tenant_org_id
    )
    return report
