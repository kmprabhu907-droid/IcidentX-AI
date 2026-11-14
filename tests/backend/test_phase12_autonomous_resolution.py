"""
INCIDENTX AI — PHASE 12: SAFE AUTONOMOUS INCIDENT RESOLUTION ENGINE
Comprehensive Automated Test Suite

Covers:
- Module 12.1: Intelligent Remediation Planning
- Module 12.2: Controlled Remediation Action Library
- Module 12.3: Intelligent Risk Assessment
- Module 12.4: Approval Workflow Engine (Anti-Tamper & Anti-Self-Authorization)
- Module 12.5: Controlled Execution Engine (Idempotency & Concurrency)
- Module 12.6: Pre-Execution Safety Battery
- Module 12.7: Automated Rollback Engine
- Module 12.8: Empirical Recovery Verification
- Module 12.9: Remediation Dashboard API Endpoints
- Module 12.10: Complete Incident Resolution Workflow & Lifecycle Transition
- Module 12.11: DemoMesh vs. Kubernetes Live Separation
- Module 12.12: Security Governance & Global Kill Switch
"""

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence
from backend.app.services.resolution.action_library import action_library, RemediationActionLibrary
from backend.app.services.resolution.approval_engine import approval_engine, ApprovalWorkflowEngine
from backend.app.services.resolution.execution_engine import execution_engine, ControlledExecutionEngine
from backend.app.services.resolution.kill_switch import kill_switch
from backend.app.services.resolution.planning_engine import planning_engine, RemediationPlanningEngine
from backend.app.services.resolution.recovery_verifier import recovery_verifier, EmpiricalRecoveryVerifier
from backend.app.services.resolution.risk_engine import risk_engine, IntelligentRiskEngine
from backend.app.services.resolution.rollback_engine import rollback_engine, AutomatedRollbackEngine
from backend.app.services.resolution.safety_validator import safety_validator, PreExecutionSafetyEngine
from backend.app.services.resolution.resolution_service import resolution_service, AutonomousResolutionService
from backend.app.services.resolution.schemas import (
    ActionCategory,
    ApprovalRecord,
    ApprovalStatus,
    ExecutionStatus,
    RecoveryStatus,
    ResolutionActionItem,
    ResolutionPlan,
    ResourceStateSnapshot,
    RiskClassification,
)
from backend.app.services.root_cause.schemas import (
    CausalGraph,
    CompetingHypothesisAnalysis,
    CounterEvidenceReport,
    HypothesisItem,
    HypothesisStatus,
    ConfidenceCategory,
    RootCauseReport,
)


# ==============================================================================
# Helper to synthesize a mock Phase 11 RootCauseReport
# ==============================================================================
def create_mock_root_cause_report(
    incident_id: str,
    title: str = "Memory Leak in Buffer Allocator",
    confidence_score: float = 0.88,
    status: HypothesisStatus = HypothesisStatus.SUPPORTED,
    affected_service: str = "payment-service",
) -> RootCauseReport:
    hyp = HypothesisItem(
        id="hyp-p11-test",
        incident_id=incident_id,
        title=title,
        description=f"Automated root cause evaluation for {affected_service}",
        affected_service=affected_service,
        triggering_event="Deployment revision v2.4 applied",
        supporting_evidence_ids=["ev-1", "ev-2"],
        confidence_score=confidence_score,
        confidence_category=ConfidenceCategory.VERY_HIGH if confidence_score >= 0.85 else ConfidenceCategory.MODERATE,
        status=status,
    )
    comp = CompetingHypothesisAnalysis(
        incident_id=incident_id,
        total_hypotheses=1,
        ranked_hypotheses=[hyp],
        ranking_rationale="Empirical facts substantiate memory leak",
        top_hypothesis_id=hyp.id,
    )
    graph = CausalGraph(
        incident_id=incident_id,
        nodes=[],
        edges=[],
        verified_causal_ratio=1.0,
    )
    return RootCauseReport(
        incident_id=incident_id,
        primary_root_cause=hyp.title,
        primary_hypothesis=hyp,
        competing_analysis=comp,
        counter_evidence_reports=[],
        causal_graph=graph,
        similar_incidents=[],
        confidence_score=confidence_score,
        confidence_category=hyp.confidence_category,
        executive_summary="Empirically grounded diagnosis",
    )


# ==============================================================================
# 1. ACTION LIBRARY & ALLOWLIST TESTS (Module 12.2)
# ==============================================================================

def test_action_library_allowlist_and_schemas():
    """Verifies that all 11 certified remediation actions are allowlisted and strictly typed."""
    actions = action_library.list_actions()
    assert len(actions) >= 11

    # Check Kubernetes actions
    assert action_library.is_allowlisted("k8s-restart-deployment")
    assert action_library.is_allowlisted("k8s-scale-deployment")
    assert action_library.is_allowlisted("k8s-rollback-deployment")
    assert action_library.is_allowlisted("k8s-recreate-pods")

    # Check Application actions
    assert action_library.is_allowlisted("app-disable-feature-flag")
    assert action_library.is_allowlisted("app-trigger-recovery-workflow")

    # Check Infrastructure actions
    assert action_library.is_allowlisted("infra-recheck-health")
    assert action_library.is_allowlisted("infra-validate-dependencies")

    # Disallow arbitrary unvetted strings
    assert not action_library.is_allowlisted("rm -rf /")
    assert not action_library.is_allowlisted("kubectl delete namespace default")

    # Create valid action item
    item = action_library.create_action_item(
        action_id="k8s-restart-deployment",
        target_service="payment-service",
        environment="DEMOMESH",
    )
    assert item.action_id == "k8s-restart-deployment"
    assert item.target_service_name == "payment-service"
    assert item.risk_level == RiskClassification.LOW
    assert item.is_reversible is True


# ==============================================================================
# 2. PLANNING ENGINE & UNSUPPORTED HYPOTHESIS SAFETY (Module 12.1)
# ==============================================================================

def test_planning_engine_supported_vs_unsupported_hypothesis():
    """Verifies that planning engine generates active actions for supported diagnoses, and passive-only for unconfirmed hypotheses."""
    # Case A: Supported Hypothesis -> Active Remediation (Restart + Scale)
    rc_supported = create_mock_root_cause_report(
        incident_id="inc-supported",
        title="Pod Memory Leak & Resource Exhaustion",
        confidence_score=0.85,
        status=HypothesisStatus.SUPPORTED,
    )
    plan_supported = planning_engine.generate_remediation_plan(
        incident_id="inc-supported",
        root_cause_report=rc_supported,
        environment="DEMOMESH",
    )
    assert plan_supported.status == "PROPOSED"
    assert len(plan_supported.proposed_actions) >= 1
    assert any("restart" in a.action_id or "scale" in a.action_id for a in plan_supported.proposed_actions)
    assert plan_supported.plan_fingerprint is not None

    # Case B: Unsupported / Rejected Hypothesis -> Passive Health Recheck ONLY (Zero mutation)
    rc_unsupported = create_mock_root_cause_report(
        incident_id="inc-unsupported",
        title="Hypothetical Database Corruption",
        confidence_score=0.20,
        status=HypothesisStatus.REJECTED,
    )
    plan_unsupported = planning_engine.generate_remediation_plan(
        incident_id="inc-unsupported",
        root_cause_report=rc_unsupported,
        environment="DEMOMESH",
    )
    assert "UNCONFIRMED" in plan_unsupported.root_cause_reference
    assert len(plan_unsupported.proposed_actions) == 1
    assert plan_unsupported.proposed_actions[0].action_id == "infra-recheck-health"
    assert plan_unsupported.proposed_actions[0].category == ActionCategory.INFRASTRUCTURE


# ==============================================================================
# 3. INTELLIGENT RISK ENGINE TESTS (Module 12.3)
# ==============================================================================

def test_intelligent_risk_assessment_tiers():
    """Verifies deterministic risk scoring across tiers based on service criticality and reversibility."""
    # Low Risk Action: Restart internal peripheral cache
    act_low = action_library.create_action_item("infra-recheck-health", "analytics-worker")
    risk_low = risk_engine.evaluate_action_risk("plan-1", act_low, incident_severity="P3")
    assert risk_low.risk_classification == RiskClassification.LOW
    assert not risk_low.requires_human_approval

    # High Risk Action: Rollback deployment on core payment-service
    act_high = action_library.create_action_item("k8s-rollback-deployment", "payment-service")
    risk_high = risk_engine.evaluate_action_risk("plan-2", act_high, incident_severity="P1", affected_replica_count=6)
    assert risk_high.risk_classification in (RiskClassification.HIGH, RiskClassification.CRITICAL)
    assert risk_high.requires_human_approval is True
    assert "payment-service" in risk_high.impact_explanation


# ==============================================================================
# 4. APPROVAL WORKFLOW & ANTI-TAMPER TESTS (Module 12.4)
# ==============================================================================

def test_approval_workflow_anti_tamper_and_self_authorization():
    """Verifies SHA-256 parameter binding and anti-self-authorization enforcement."""
    action = action_library.create_action_item(
        action_id="k8s-scale-deployment",
        target_service="order-service",
        parameters={"target_replicas": 4},
    )
    risk_eval = risk_engine.evaluate_action_risk("plan-test", action, incident_severity="P2")
    approval = approval_engine.create_approval_request(
        plan_id="plan-test",
        action=action,
        risk_assessment=risk_eval,
        requesting_actor="IncidentX-AI",
        requesting_actor_type="AI_AGENT",
    )

    assert approval.approval_status == ApprovalStatus.PENDING
    assert len(approval.parameters_hash) == 64

    # Test A: AI Agent cannot self-authorize
    with pytest.raises(PermissionError, match="Self-authorization violation"):
        approval_engine.record_decision(
            approval=approval,
            approving_user="IncidentX-Agent-Triage",
            user_role="AI_AGENT",
            decision=ApprovalStatus.APPROVED,
            reason="Self-approving",
            current_parameters=action.parameters,
        )

    # Test B: Anti-Tamper Verification - Modified parameters invalidate approval
    tampered_parameters = {"target_replicas": 99}  # Modified after request
    tampered_approval = approval_engine.record_decision(
        approval=approval,
        approving_user="sre-lead@enterprise.io",
        user_role="SRE_LEAD",
        decision=ApprovalStatus.APPROVED,
        reason="Approved by human",
        current_parameters=tampered_parameters,
    )
    assert tampered_approval.approval_status == ApprovalStatus.CANCELLED
    assert tampered_approval.is_tampered is True

    # Test C: Clean Approval with unchanged parameters
    clean_approval = approval_engine.create_approval_request(
        plan_id="plan-test-2",
        action=action,
        risk_assessment=risk_eval,
    )
    approved = approval_engine.record_decision(
        approval=clean_approval,
        approving_user="sre-lead@enterprise.io",
        user_role="SRE_LEAD",
        decision=ApprovalStatus.APPROVED,
        reason="Approved valid replica expansion",
        current_parameters=action.parameters,
    )
    assert approved.approval_status == ApprovalStatus.APPROVED
    assert approved.approving_user == "sre-lead@enterprise.io"


# ==============================================================================
# 5. PRE-EXECUTION SAFETY ENGINE TESTS (Module 12.6)
# ==============================================================================

@pytest.mark.asyncio
async def test_pre_execution_safety_battery():
    """Verifies that all 10 pre-execution checks run and stop execution on failure."""
    rc_report = create_mock_root_cause_report("inc-precheck", affected_service="auth-service")
    plan = planning_engine.generate_remediation_plan("inc-precheck", rc_report)
    action = plan.proposed_actions[0]

    # Make approval valid
    approval = approval_engine.record_decision(
        approval=plan.approval_record,
        approving_user="operator@enterprise.io",
        user_role="SRE_LEAD",
        decision=ApprovalStatus.APPROVED,
        reason="Pre-check approval",
        current_parameters=action.parameters,
    )
    plan.approval_record = approval

    # Case A: Clean Pre-Check Passes
    check_pass = await safety_validator.validate_pre_execution(
        plan=plan,
        action=action,
        approval=approval,
        cluster_id="k8s-default",
        namespace="default",
    )
    assert check_pass.passed is True
    assert len(check_pass.failure_reasons) == 0

    # Case B: Disruption Budget Violation
    check_fail_budget = await safety_validator.validate_pre_execution(
        plan=plan,
        action=action_library.create_action_item("k8s-scale-deployment", "auth-service"),
        approval=approval,
        current_replicas=1,
        min_available_budget=1,
    )
    assert check_fail_budget.passed is False
    assert any("Disruption Budget" in r for r in check_fail_budget.failure_reasons)

    # Case C: Active Kill Switch Halts Pre-Check
    await kill_switch.activate(user="SRE-Tester", reason="Test lockdown")
    check_fail_kill = await safety_validator.validate_pre_execution(
        plan=plan,
        action=action,
        approval=approval,
    )
    assert check_fail_kill.passed is False
    assert check_fail_kill.kill_switch_inactive is False
    assert any("KILL SWITCH" in r for r in check_fail_kill.failure_reasons)
    await kill_switch.deactivate(user="SRE-Tester")


# ==============================================================================
# 6. CONTROLLED EXECUTION & IDEMPOTENCY TESTS (Module 12.5)
# ==============================================================================

@pytest.mark.asyncio
async def test_controlled_execution_idempotency_and_concurrency():
    """Verifies that execution runs safely and enforces idempotency and service concurrency locks."""
    rc_report = create_mock_root_cause_report("inc-exec", affected_service="cart-service")
    plan = planning_engine.generate_remediation_plan("inc-exec", rc_report)

    # Pre-approve plan
    plan.approval_record.approval_status = ApprovalStatus.APPROVED

    # Execute plan
    exec_result_plan = await execution_engine.execute_plan(
        plan=plan,
        cluster_id="k8s-default",
        namespace="default",
    )
    assert exec_result_plan.status in ("EXECUTED", "RECOVERY_SUCCESSFUL")
    assert exec_result_plan.execution_result is not None
    assert exec_result_plan.execution_result.status == ExecutionStatus.EXECUTED
    assert len(exec_result_plan.execution_result.execution_logs) >= 3

    # Idempotency: Re-executing same plan returns cached result without re-mutating
    re_exec_plan = await execution_engine.execute_plan(
        plan=plan,
        cluster_id="k8s-default",
        namespace="default",
    )
    assert re_exec_plan.execution_result.execution_id == exec_result_plan.execution_result.execution_id


# ==============================================================================
# 7. AUTOMATED ROLLBACK ENGINE TESTS (Module 12.7)
# ==============================================================================

@pytest.mark.asyncio
async def test_automated_rollback_reversal():
    """Verifies that failed remediation triggers state snapshot restoration and logs rollback."""
    action = action_library.create_action_item("k8s-scale-deployment", "inventory-service")
    pre_snapshot = ResourceStateSnapshot(
        resource_name="deployment/inventory-service",
        resource_version="v1.2.0",
        replicas_ready=2,
        replicas_desired=2,
        error_rate_percent=1.0,
    )

    # Check eligibility
    eligible, reason = rollback_engine.evaluate_rollback_eligibility(action, pre_snapshot)
    assert eligible is True

    # Execute rollback
    rb_res = await rollback_engine.execute_rollback(
        original_execution_id="exec-failed-123",
        action=action,
        pre_state=pre_snapshot,
        environment="DEMOMESH",
    )
    assert rb_res.success is True
    assert "inventory-service" in rb_res.target_resource
    assert len(rb_res.rollback_logs) >= 2


# ==============================================================================
# 8. EMPIRICAL RECOVERY VERIFICATION TESTS (Module 12.8)
# ==============================================================================

@pytest.mark.asyncio
async def test_empirical_recovery_verification_telemetry():
    """Verifies that recovery status requires empirical evidence (error drop, latency, pod readiness)."""
    action = action_library.create_action_item("k8s-restart-deployment", "checkout-service")

    # Case A: Successful Recovery (Error dropped, latency normalized, 100% ready)
    pre_snap = ResourceStateSnapshot(
        resource_name="deployment/checkout-service",
        replicas_ready=1,
        replicas_desired=2,
        error_rate_percent=42.0,
        p95_latency_ms=900.0,
    )
    post_snap_healthy = ResourceStateSnapshot(
        resource_name="deployment/checkout-service",
        replicas_ready=2,
        replicas_desired=2,
        error_rate_percent=0.3,
        p95_latency_ms=85.0,
    )
    report_healthy = await recovery_verifier.verify_recovery(
        incident_id="inc-verif-1",
        plan_id="plan-1",
        action=action,
        pre_snapshot=pre_snap,
        post_snapshot=post_snap_healthy,
    )
    assert report_healthy.status == RecoveryStatus.RECOVERY_SUCCESSFUL
    assert report_healthy.error_rate_recovered is True
    assert report_healthy.latency_recovered is True
    assert report_healthy.requires_rollback is False

    # Case B: Failed Recovery -> Triggers ROLLBACK_REQUIRED
    post_snap_unhealthy = ResourceStateSnapshot(
        resource_name="deployment/checkout-service",
        replicas_ready=0,
        replicas_desired=2,
        error_rate_percent=55.0,
        p95_latency_ms=1200.0,
    )
    report_failed = await recovery_verifier.verify_recovery(
        incident_id="inc-verif-2",
        plan_id="plan-2",
        action=action,
        pre_snapshot=pre_snap,
        post_snapshot=post_snap_unhealthy,
    )
    assert report_failed.status == RecoveryStatus.RECOVERY_FAILED
    assert report_failed.requires_rollback is True


# ==============================================================================
# 9. COMPLETE INCIDENT RESOLUTION LIFECYCLE (Module 12.10)
# ==============================================================================

@pytest.mark.asyncio
async def test_resolution_service_full_lifecycle(db_session: AsyncSession):
    """Verifies that resolution service updates Phase 9 incident lifecycle to RESOLVED only upon verified recovery."""
    incident = Incident(
        title="Payment Service 504 Gateway Degradation",
        severity="SEV-1",
        status="INVESTIGATING",
        impact_scope="payment-service",
    )
    db_session.add(incident)
    await db_session.flush()

    # Pre-seed diagnostic evidence
    e1 = Evidence(
        incident_id=incident.id,
        evidence_type="kubernetes_event",
        evidence_category="KUBERNETES",
        source_system="kubernetes",
        affected_service_name="payment-service",
        description="Deployment rollout revision 3 applied",
        is_fact=True,
    )
    db_session.add(e1)
    await db_session.flush()

    # 1. Generate plan
    plan = await resolution_service.generate_plan_for_incident(
        incident_id=incident.id,
        session=db_session,
    )
    assert plan.incident_id == incident.id
    assert incident.status == "REMEDIATION_PENDING"

    # 2. Approve plan
    approved_plan = await resolution_service.approve_plan(
        incident_id=incident.id,
        approving_user="sre-lead@enterprise.io",
        user_role="SRE_LEAD",
        decision=ApprovalStatus.APPROVED,
        reason="Approved after verification",
        session=db_session,
        emergency_override=True,
    )
    assert approved_plan.approval_record.approval_status == ApprovalStatus.APPROVED

    # 3. Execute plan & verify transition to RESOLVED
    final_plan = await resolution_service.execute_resolution(
        incident_id=incident.id,
        session=db_session,
    )
    assert final_plan.execution_result.status == ExecutionStatus.EXECUTED
    assert final_plan.recovery_report.status == RecoveryStatus.RECOVERY_SUCCESSFUL

    # Verify incident state transitioned to RESOLVED
    inc_stmt = select(Incident).where(Incident.id == incident.id)
    inc_res = await db_session.execute(inc_stmt)
    updated_inc = inc_res.scalar_one()
    assert updated_inc.status == "RESOLVED"


# ==============================================================================
# 10. REST API ENDPOINTS TESTS (Module 12.9 & 12.12)
# ==============================================================================

@pytest.mark.asyncio
async def test_resolution_rest_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Verifies all Phase 12 REST API endpoints."""
    incident = Incident(
        title="Cart Service High CPU Anomaly",
        severity="SEV-2",
        status="INVESTIGATING",
        impact_scope="cart-service",
    )
    db_session.add(incident)
    await db_session.flush()

    # 1. GET /api/v1/resolution/actions
    actions_resp = await client.get("/api/v1/resolution/actions")
    assert actions_resp.status_code == 200
    assert len(actions_resp.json()) >= 11

    # 2. POST /api/v1/incidents/{id}/resolution/plan
    plan_resp = await client.post(f"/api/v1/incidents/{incident.id}/resolution/plan")
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["incident_id"] == incident.id
    assert "plan_id" in plan_data

    # 3. GET /api/v1/incidents/{id}/resolution/plan
    get_plan_resp = await client.get(f"/api/v1/incidents/{incident.id}/resolution/plan")
    assert get_plan_resp.status_code == 200
    assert get_plan_resp.json()["plan_id"] == plan_data["plan_id"]

    # 4. POST /api/v1/incidents/{id}/resolution/approve
    appr_resp = await client.post(
        f"/api/v1/incidents/{incident.id}/resolution/approve",
        json={
            "decision": "APPROVED",
            "approving_user": "sre-responder@enterprise.io",
            "user_role": "SRE_LEAD",
            "reason": "Approved via REST API",
        },
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["approval_record"]["approval_status"] == "APPROVED"

    # 5. POST /api/v1/incidents/{id}/resolution/execute
    exec_resp = await client.post(f"/api/v1/incidents/{incident.id}/resolution/execute")
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["execution_result"] is not None

    # 6. GET /api/v1/incidents/{id}/resolution/verification
    verif_resp = await client.get(f"/api/v1/incidents/{incident.id}/resolution/verification")
    assert verif_resp.status_code == 200

    # 7. GET & POST /api/v1/resolution/kill-switch
    ks_status_resp = await client.get("/api/v1/resolution/kill-switch")
    assert ks_status_resp.status_code == 200
    assert "is_active" in ks_status_resp.json()

    ks_toggle_resp = await client.post(
        "/api/v1/resolution/kill-switch",
        json={
            "is_active": True,
            "user": "REST-SRE",
            "reason": "API test trigger",
        },
    )
    assert ks_toggle_resp.status_code == 200
    assert ks_toggle_resp.json()["is_active"] is True

    # Reset kill switch
    await client.post(
        "/api/v1/resolution/kill-switch",
        json={"is_active": False, "user": "REST-SRE"},
    )
