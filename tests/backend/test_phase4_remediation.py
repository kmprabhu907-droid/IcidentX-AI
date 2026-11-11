"""
INCIDENTX AI - Phase 4 Remediation & Self-Healing Engine Tests
Comprehensive verification of the Action Registry, Intelligence Engine, Safety & Approval Gates,
Execution Sandbox, Recovery Verification, Rollback Controls, and Emergency Stop.
"""

import asyncio
from datetime import datetime, timezone
import json
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.database import async_session_factory
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.remediation import RemediationAction, RemediationPolicy
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.remediation.registry import remediation_registry
from backend.app.services.remediation.safety import RemediationSecurityException, safety_engine
from backend.app.services.simulation.chaos_controller import chaos_controller
from backend.main import app


def get_err(resp) -> str:
    body = resp.json()
    if "error" in body and isinstance(body["error"], dict):
        return body["error"].get("message", "")
    return str(body.get("detail", ""))


@pytest.fixture(autouse=True)
async def cleanup_chaos_and_safety():
    """Ensure clean state before and after each test."""
    await chaos_controller.stop_all()
    demo_mesh.clear_all_faults()
    safety_engine.emergency_stop_active = False
    safety_engine.circuit_breaker_tripped = False
    safety_engine.circuit_breaker_reason = None
    safety_engine._active_executions.clear()

    async with async_session_factory() as session:
        async with session.begin():
            policy = await safety_engine.get_or_create_policy(session)
            policy.mode = "RECOMMENDATION_ONLY"
            policy.is_autonomous_enabled = False
            policy.emergency_stop_active = False
            policy.circuit_breaker_tripped = False
            policy.circuit_breaker_reason = None
            policy.max_actions_per_incident = 3
            await session.flush()

    yield

    await chaos_controller.stop_all()
    demo_mesh.clear_all_faults()
    safety_engine.emergency_stop_active = False
    safety_engine.circuit_breaker_tripped = False


@pytest.mark.asyncio
async def test_action_registry_contains_8_predefined_safe_actions():
    """Verify registry catalog contains all 8 predefined actions with schemas and no arbitrary shell strings."""
    actions = remediation_registry.list_actions()
    assert len(actions) == 8

    action_ids = {a["action_id"] for a in actions}
    expected_ids = {
        "act-restart-service",
        "act-scale-replicas",
        "act-rollback-deployment",
        "act-clear-cache",
        "act-reset-db-pool",
        "act-toggle-feature-flag",
        "act-apply-rate-limit",
        "act-switch-dependency",
    }
    assert action_ids == expected_ids

    for act in actions:
        assert act["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert act["estimated_cost"] in ["LOW", "MEDIUM", "HIGH"]
        assert "parameter_schema" in act
        assert act["timeout_seconds"] > 0


@pytest.mark.asyncio
async def test_remediation_intelligence_generates_grounded_recommendations():
    """Verify investigated incident generates evidence-grounded recommendations with contraindications."""
    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(
                title="Postgres Connection Saturation & Checkout Failures",
                summary="Database connection pool exhausted.",
                severity="SEV-1",
                status="INVESTIGATING",
                impact_scope="postgres-db, order-service",
            )
            session.add(incident)
            await session.flush()

            hyp = RootCauseHypothesis(
                incident_id=incident.id,
                culprit_service_id="postgres-db",
                hypothesis_text="PostgreSQL connection pool exhausted by idle clients",
                probability_score=0.92,
                status="VALIDATED",
                is_confirmed_root_cause=True,
            )
            session.add(hyp)

            ev = Evidence(
                incident_id=incident.id,
                evidence_type="METRIC_DEVIATION",
                source_system="postgres-db",
                description="Database connection pool utilization at 100% capacity.",
                confidence_score=0.95,
                is_contradictory=False,
                observed_at=datetime.now(timezone.utc),
            )
            session.add(ev)
            await session.flush()
            inc_id = incident.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger recommendations
        r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/recommend")
        assert r.status_code == 200
        data = r.json()
        assert data["generated_count"] >= 2

        actions = data["actions"]
        action_ids = [a["action_id"] for a in actions]
        assert "act-reset-db-pool" in action_ids

        db_action = next(a for a in actions if a["action_id"] == "act-reset-db-pool")
        assert db_action["risk_level"] == "MEDIUM"
        assert db_action["target_service_name"] == "postgres-db"
        assert "pg_stat_activity" in db_action["recommendation_reason"]

        contra = json.loads(db_action["contraindications"])
        assert any("clear Redis cache" in c for c in contra)


@pytest.mark.asyncio
async def test_mode_a_recommendation_only_enforces_execution_lockdown():
    """Verify Mode A (RECOMMENDATION_ONLY) strictly prevents action execution."""
    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Test Incident", severity="SEV-2", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            action = RemediationAction(
                incident_id=incident.id,
                action_id="act-clear-cache",
                name="Clear Cache",
                description="Test",
                action_type="cache",
                target_service_name="redis-cache",
                parameters=json.dumps({"service_name": "redis-cache", "cache_pattern": "ALL"}),
                risk_level="LOW",
                idempotency_key="test-key-mode-a",
                status="PROPOSED",
                approval_status="APPROVED",
                approved_by="human-admin",
                expected_outcome="Restores cache performance",
            )
            session.add(action)
            await session.flush()
            act_id = action.id
            inc_id = incident.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt execution while mode is RECOMMENDATION_ONLY
        r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert r.status_code == 403
        assert "RECOMMENDATION_ONLY" in get_err(r)


@pytest.mark.asyncio
async def test_mode_b_human_approval_enforcement():
    """Verify Mode B rejects unapproved actions and allows execution once approved."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Set mode to HUMAN_APPROVAL
        await client.put("/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Test Incident", severity="SEV-2", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            action = RemediationAction(
                incident_id=incident.id,
                action_id="act-restart-service",
                name="Restart Service",
                description="Test restart",
                action_type="restart",
                target_service_name="order-service",
                parameters=json.dumps({"service_name": "order-service", "grace_period_seconds": 5}),
                risk_level="LOW",
                idempotency_key="test-key-mode-b",
                status="PROPOSED",
                approval_status="PENDING",
                expected_outcome="Restores service health",
            )
            session.add(action)
            await session.flush()
            act_id = action.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Attempt unapproved execution -> Rejected
        r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert r.status_code == 403
        assert "requires explicit human approval" in get_err(r)

        # 2. Approve action
        appr_r = await client.post(
            f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/approve",
            json={"approved_by": "alice@incidentx.ai", "comment": "Verified safe to execute"}
        )
        assert appr_r.status_code == 200
        assert appr_r.json()["approval_status"] == "APPROVED"
        assert appr_r.json()["approved_by"] == "alice@incidentx.ai"

        # 3. Execute approved action -> Success
        exec_r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert exec_r.status_code == 200
        res = exec_r.json()
        assert res["status"] == "EXECUTED"
        assert res["verification_status"] in ["VERIFIED", "PARTIALLY_VERIFIED"]


@pytest.mark.asyncio
async def test_mode_c_autonomous_mode_blocks_high_risk_actions_without_approval():
    """Verify Mode C (CONTROLLED_AUTONOMOUS) blocks HIGH risk operations without human approval."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Set mode to CONTROLLED_AUTONOMOUS
        await client.put("/api/v1/remediation/policy", json={"mode": "CONTROLLED_AUTONOMOUS"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="High Risk Failover", severity="SEV-1", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            # High risk action: act-switch-dependency
            high_risk_act = RemediationAction(
                incident_id=incident.id,
                action_id="act-switch-dependency",
                name="Switch Payment Gateway",
                description="High risk failover",
                action_type="switch_dep",
                target_service_name="payment-service",
                parameters=json.dumps({"service_name": "payment-service", "dependency_name": "psp", "target_endpoint": "fallback"}),
                risk_level="HIGH",
                idempotency_key="test-key-high-risk",
                status="PROPOSED",
                approval_status="PENDING",
                expected_outcome="Diverts traffic",
            )
            session.add(high_risk_act)
            await session.flush()
            act_id = high_risk_act.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Autonomous trigger on HIGH risk action -> Rejected
        r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute?is_autonomous=true")
        assert r.status_code == 403
        assert "ALWAYS require human approval" in get_err(r)


@pytest.mark.asyncio
async def test_invalid_parameters_and_precondition_failures():
    """Verify Pydantic validation rejects invalid parameters and precondition checks halt execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.put("/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Test Preconditions", severity="SEV-2", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            # 1. Invalid parameter (scale target < 1)
            bad_param_act = RemediationAction(
                incident_id=incident.id,
                action_id="act-scale-replicas",
                name="Invalid Scale",
                description="Scale with 0 replicas",
                action_type="scale",
                target_service_name="order-service",
                parameters=json.dumps({"service_name": "order-service", "target_replicas": 0}),
                risk_level="LOW",
                idempotency_key="test-bad-param",
                status="APPROVED",
                approval_status="APPROVED",
                approved_by="operator",
                expected_outcome="Scale replicas",
            )
            # 2. Failed precondition (non-existent service)
            bad_precond_act = RemediationAction(
                incident_id=incident.id,
                action_id="act-restart-service",
                name="Bad Service Restart",
                description="Restart unknown service",
                action_type="restart",
                target_service_name="nonexistent-svc",
                parameters=json.dumps({"service_name": "nonexistent-svc", "grace_period_seconds": 5}),
                risk_level="LOW",
                idempotency_key="test-bad-precond",
                status="APPROVED",
                approval_status="APPROVED",
                approved_by="operator",
                expected_outcome="Restart service",
            )
            session.add_all([bad_param_act, bad_precond_act])
            await session.flush()
            bad_param_id = bad_param_act.id
            bad_precond_id = bad_precond_act.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{bad_param_id}/execute")
        assert r1.status_code == 400
        assert "Parameter validation failed" in get_err(r1)

        r2 = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{bad_precond_id}/execute")
        assert r2.status_code == 400
        assert "Precondition failed" in get_err(r2)


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_executions():
    """Verify duplicate executions of the same action record are rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.put("/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Idempotency Test", severity="SEV-3", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            action = RemediationAction(
                incident_id=incident.id,
                action_id="act-clear-cache",
                name="Clear Cache",
                description="Test",
                action_type="cache",
                target_service_name="redis-cache",
                parameters=json.dumps({"service_name": "redis-cache", "cache_pattern": "ALL"}),
                risk_level="LOW",
                idempotency_key="unique-idemp-key-123",
                status="APPROVED",
                approval_status="APPROVED",
                approved_by="operator",
                expected_outcome="Clear cache",
            )
            session.add(action)
            await session.flush()
            act_id = action.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First execution succeeds
        r1 = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert r1.status_code == 200

        # Second execution on same record fails idempotency check
        r2 = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert r2.status_code == 400
        assert "already been processed" in get_err(r2)


@pytest.mark.asyncio
async def test_emergency_stop_trips_circuit_breaker_and_halts_all():
    """Verify Emergency Stop endpoint immediately trips circuit breaker and locks down execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Set mode to HUMAN_APPROVAL
        await client.put("/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Emergency Stop Test", severity="SEV-2", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            action = RemediationAction(
                incident_id=incident.id,
                action_id="act-clear-cache",
                name="Clear Cache",
                description="Test",
                action_type="cache",
                target_service_name="redis-cache",
                parameters=json.dumps({"service_name": "redis-cache", "cache_pattern": "ALL"}),
                risk_level="LOW",
                idempotency_key="test-key-em-stop",
                status="APPROVED",
                approval_status="APPROVED",
                approved_by="operator",
                expected_outcome="Clear cache",
            )
            session.add(action)
            await session.flush()
            act_id = action.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Trigger Emergency Stop
        em_r = await client.post("/api/v1/remediation/emergency-stop", json={"reason": "Operator observed critical telemetry drift"})
        assert em_r.status_code == 200
        pol = em_r.json()
        assert pol["emergency_stop_active"] is True
        assert pol["circuit_breaker_tripped"] is True
        assert pol["mode"] == "RECOMMENDATION_ONLY"

        # 3. Attempting execution is immediately rejected
        r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert r.status_code == 403
        assert "EMERGENCY STOP is active" in get_err(r)

        # 4. Reset circuit breaker
        reset_r = await client.post("/api/v1/remediation/reset-circuit-breaker")
        assert reset_r.status_code == 200
        assert reset_r.json()["circuit_breaker_tripped"] is False
        assert reset_r.json()["emergency_stop_active"] is False


@pytest.mark.asyncio
async def test_manual_rollback_lifecycle():
    """Verify manual rollback endpoint restores previous simulated state and updates status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.put("/api/v1/remediation/policy", json={"mode": "HUMAN_APPROVAL"})

    async with async_session_factory() as session:
        async with session.begin():
            incident = Incident(title="Rollback Test", severity="SEV-2", status="INVESTIGATING")
            session.add(incident)
            await session.flush()

            action = RemediationAction(
                incident_id=incident.id,
                action_id="act-scale-replicas",
                name="Scale Replicas",
                description="Scale",
                action_type="scale",
                target_service_name="order-service",
                parameters=json.dumps({"service_name": "order-service", "target_replicas": 4, "current_replicas": 2}),
                risk_level="LOW",
                idempotency_key="rollback-test-key",
                status="APPROVED",
                approval_status="APPROVED",
                approved_by="operator",
                expected_outcome="Scale replicas",
            )
            session.add(action)
            await session.flush()
            act_id = action.id
            inc_id = incident.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Execute
        exec_r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/execute")
        assert exec_r.status_code == 200
        assert exec_r.json()["status"] == "EXECUTED"
        assert exec_r.json()["rollback_status"] == "AVAILABLE"

        # Rollback
        rb_r = await client.post(f"/api/v1/incidents/{inc_id}/remediation/actions/{act_id}/rollback?operator=bob")
        assert rb_r.status_code == 200
        res = rb_r.json()
        assert res["rollback_status"] == "ROLLED_BACK"
        assert "Scaled order-service back down" in res["rollback_log"]
