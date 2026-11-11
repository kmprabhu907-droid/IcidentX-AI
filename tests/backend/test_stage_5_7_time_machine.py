"""
INCIDENTX AI - Stage 5.7 Incident Time Machine & Causal Graph Tests
Validates chronological correlation across metrics, logs, traces, hypotheses,
remediations, and regressions, NetworkX causal topology, state transitions, and FastAPI endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.reliability import RegressionRecord
from backend.app.models.remediation import RemediationAction
from backend.app.services.time_machine import (
    CausalGraphBuilder,
    IncidentTimeMachineEngine,
)


@pytest.fixture
def sample_incident_setup():
    now = datetime.now(timezone.utc)
    return {
        "title": "Database Connection Pool Starvation in order-service",
        "summary": "Connection pool reached 100% capacity",
        "severity": "SEV-1",
        "status": "RESOLVED",
        "impact_scope": "order-service, postgres-db",
        "detected_at": now - timedelta(minutes=20),
        "resolved_at": now - timedelta(minutes=5),
        "mttr_seconds": 900.0,
    }


# 1. Base topology construction with NetworkX
def test_01_networkx_base_topology():
    g = CausalGraphBuilder.get_base_topology_graph()
    assert len(g.nodes) >= 6
    assert len(g.edges) >= 8
    assert g.has_edge("api-gateway", "order-service")
    assert g.has_edge("order-service", "postgres-db")


# 2. Failure propagation path calculation
def test_02_failure_propagation_path():
    causal = CausalGraphBuilder.analyze_incident_causality(
        primary_service="postgres-db",
        affected_services=["order-service", "postgres-db"],
    )
    assert len(causal.impacted_path) >= 2
    assert "api-gateway" in causal.impacted_path
    assert "postgres-db" in causal.impacted_path


# 3. Structural blast radius scoring
def test_03_blast_radius_scoring():
    causal = CausalGraphBuilder.analyze_incident_causality(
        primary_service="order-service",
        affected_services=["order-service", "postgres-db", "payment-service"],
    )
    assert 20.0 <= causal.blast_radius_score <= 100.0


# 4. Causal node root cause candidate attribution
def test_04_causal_node_attribution():
    causal = CausalGraphBuilder.analyze_incident_causality(
        primary_service="postgres-db",
        affected_services=["order-service", "postgres-db"],
    )
    db_node = next(n for n in causal.nodes if n.id == "postgres-db")
    assert db_node.is_root_cause_candidate is True
    assert db_node.health_status == "FAILING"

    gw_node = next(n for n in causal.nodes if n.id == "api-gateway")
    assert gw_node.is_root_cause_candidate is False


# 5. Causal edge impact path annotation
def test_05_causal_edge_impact_annotation():
    causal = CausalGraphBuilder.analyze_incident_causality(
        primary_service="order-service",
        affected_services=["order-service"],
    )
    # The edge from api-gateway to order-service should be on the impact path
    edge = next(e for e in causal.edges if e.source == "api-gateway" and e.target == "order-service")
    assert edge.is_impact_path is True


# 6. Full timeline assembly for incident
@pytest.mark.asyncio
async def test_06_build_incident_timeline(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    assert report is not None
    assert report.incident_id == inc.id
    assert len(report.timeline_events) >= 3
    assert len(report.lifecycle_phases) >= 4


# 7. Chronological ordering of timeline events
@pytest.mark.asyncio
async def test_07_timeline_events_chronological_order(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    timestamps = [e.timestamp for e in report.timeline_events]
    assert timestamps == sorted(timestamps)


# 8. Correlated evidence in timeline
@pytest.mark.asyncio
async def test_08_evidence_correlation(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    ev = Evidence(
        incident_id=inc.id,
        evidence_type="error_log",
        source_system="order-service",
        description="FATAL: remaining connection slots are reserved",
        confidence_score=0.98,
        verification_status="VERIFIED",
    )
    db_session.add(ev)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    log_events = [e for e in report.timeline_events if e.event_type == "LOG_RECORD"]
    assert len(log_events) >= 1
    assert "remaining connection slots" in log_events[0].summary


# 9. Correlated root cause hypotheses in timeline
@pytest.mark.asyncio
async def test_09_hypothesis_correlation(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    hyp = RootCauseHypothesis(
        incident_id=inc.id,
        hypothesis_text="Postgres DB pool exhausted due to unclosed sessions in order-service",
        probability_score=0.94,
        status="ACCEPTED",
        is_confirmed_root_cause=True,
    )
    db_session.add(hyp)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    hyp_events = [e for e in report.timeline_events if e.event_type == "HYPOTHESIS_FORMED"]
    assert len(hyp_events) >= 1
    assert "unclosed sessions" in hyp_events[0].summary


# 10. Correlated safe remediation actions in timeline
@pytest.mark.asyncio
async def test_10_remediation_correlation(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    rem = RemediationAction(
        incident_id=inc.id,
        action_id="act-reset-db-pool",
        name="Reset Connection Pool",
        description="Recycle stale DB connections",
        action_type="db_pool",
        expected_outcome="Restore pool connections",
        idempotency_key=f"idem-rem-{inc.id}",
        target_service_name="postgres-db",
        risk_level="MEDIUM",
        status="EXECUTED",
        verification_status="VERIFIED",
    )
    db_session.add(rem)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    act_events = [e for e in report.timeline_events if e.event_type == "ACTION_EXECUTED"]
    assert len(act_events) >= 1
    assert "act-reset-db-pool" in act_events[0].summary


# 11. Correlated verification in timeline
@pytest.mark.asyncio
async def test_11_verification_correlation(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    rem = RemediationAction(
        incident_id=inc.id,
        action_id="act-restart-service",
        name="Restart Order Service",
        description="Restart pod",
        action_type="restart",
        expected_outcome="Clear memory",
        idempotency_key=f"idem-ver-{inc.id}",
        target_service_name="order-service",
        status="EXECUTED",
        verification_status="VERIFIED",
    )
    db_session.add(rem)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    ver_events = [e for e in report.timeline_events if e.phase == "VERIFICATION"]
    assert len(ver_events) >= 1
    assert "PASSED" in ver_events[0].summary


# 12. Correlated regression records in timeline
@pytest.mark.asyncio
async def test_12_regression_correlation(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    reg = RegressionRecord(
        incident_id=inc.id,
        service_name="order-service",
        metric_name="db_pool_utilization",
        baseline_value=15.0,
        post_remediation_value=20.0,
        current_value=92.0,
        regression_score=0.88,
        classification="LIKELY_REGRESSION",
        status="ACTIVE",
    )
    db_session.add(reg)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    assert "REGRESSION" in report.lifecycle_phases
    reg_events = [e for e in report.timeline_events if e.event_type == "REGRESSION_DETECTED"]
    assert len(reg_events) >= 1


# 13. State transitions generation
@pytest.mark.asyncio
async def test_13_state_transitions(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    transitions = report.state_transitions
    assert "HEALTHY_BASELINE" in transitions
    assert "DETECTION" in transitions
    assert "MITIGATION" in transitions
    assert "POST_RECOVERY" in transitions


# 14. Metrics delta across states
@pytest.mark.asyncio
async def test_14_state_metrics_comparison(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    baseline = report.state_transitions["HEALTHY_BASELINE"]
    detection = report.state_transitions["DETECTION"]

    # Baseline health is HEALTHY; detection health is CRITICAL
    assert baseline.overall_health == "HEALTHY"
    assert detection.overall_health == "CRITICAL"
    assert detection.active_anomalies_count > baseline.active_anomalies_count


# 15. Point-in-time state reconstruction
@pytest.mark.asyncio
async def test_15_get_state_at_timestamp(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    # Query state at detection time
    snap = await IncidentTimeMachineEngine.get_state_at_timestamp(
        incident_id=inc.id,
        target_timestamp_str=inc.detected_at.isoformat(),
        db=db_session,
    )
    assert snap.phase == "DETECTION"
    assert snap.overall_health == "CRITICAL"


# 16. Non-existent incident returns None
@pytest.mark.asyncio
async def test_16_nonexistent_incident(db_session: AsyncSession):
    report = await IncidentTimeMachineEngine.build_incident_timeline("non-existent-uuid", db_session)
    assert report is None


# 17. Causal graph state generation
@pytest.mark.asyncio
async def test_17_get_causal_graph_state(db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    graph = await IncidentTimeMachineEngine.get_causal_graph_state(inc.id, db=db_session)
    assert len(graph.nodes) >= 6
    assert len(graph.edges) >= 8
    assert len(graph.impacted_path) >= 1


# 18. API: GET /api/v1/reliability/time-machine/{incident_id}
@pytest.mark.asyncio
async def test_18_api_get_time_machine(client: AsyncClient, db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    resp = await client.get(f"/api/v1/reliability/time-machine/{inc.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == inc.id
    assert "timeline_events" in data
    assert "state_transitions" in data
    assert "causal_graph" in data


# 19. API: GET /api/v1/reliability/time-machine/{incident_id}/state-at/{timestamp}
@pytest.mark.asyncio
async def test_19_api_get_state_at_timestamp(client: AsyncClient, db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    ts = inc.detected_at.isoformat()
    resp = await client.get(f"/api/v1/reliability/time-machine/{inc.id}/state-at/{ts}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "DETECTION"
    assert "service_metrics" in data


# 20. API: GET /api/v1/reliability/time-machine/{incident_id}/causal-graph
@pytest.mark.asyncio
async def test_20_api_get_causal_graph(client: AsyncClient, db_session: AsyncSession, sample_incident_setup):
    inc = Incident(**sample_incident_setup)
    db_session.add(inc)
    await db_session.commit()

    resp = await client.get(f"/api/v1/reliability/time-machine/{inc.id}/causal-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "impacted_path" in data
    assert data["blast_radius_score"] >= 0.0
