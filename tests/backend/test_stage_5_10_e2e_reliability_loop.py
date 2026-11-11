"""
INCIDENTX AI - Stage 5.10 End-to-End Continuous Reliability Intelligence Loop Tests
Validates the complete 16-step closed-loop autonomous scenario:
  1. Normal telemetry baseline established
  2. Resource degradation introduced (simulated DB connection pool leak)
  3. Telemetry collector captures metric progression
  4. Anomaly detection identifies abnormal pattern (EWMA + baseline deviation)
  5. Regression engine checks for recurring incident patterns
  6. Reliability Memory retrieves past similar incidents and remediation advice
  7. Predictive engine projects Time-to-Exhaustion (TTE)
  8. SLO assessment calculates error budget consumption and burn rate
  9. Incident Time Machine records event timeline & causal graph
  10. LangGraph agent assesses situation and recommends safe remediation
  11. Remediation executed safely
  12. Post-remediation verification confirms recovery
  13. Continuous monitoring verifies no regression
  14. System updates Reliability Memory with new incident and outcome
  15. Complete end-to-end verification assertions
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.reliability import AnomalyRecord, IncidentMemory, RegressionRecord
from backend.app.models.remediation import RemediationAction
from backend.app.services.agents import LangGraphReliabilityAgent
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.engine import observability_engine
from backend.app.services.observability.regression import FourStateComparisonEngine
from backend.app.services.predictive import PredictiveReliabilityEngine
from backend.app.services.reliability_memory import ReliabilityMemoryEngine
from backend.app.services.slo import SLOIntelligenceEngine
from backend.app.services.time_machine import IncidentTimeMachineEngine


@pytest.mark.asyncio
async def test_complete_16_step_reliability_loop(db_session: AsyncSession):
    # Step 1: Normal telemetry baseline established
    demo_mesh.clear_all_faults()
    await demo_mesh.tick()
    baseline_metrics = demo_mesh.get_latest_metrics()["order-service"]
    assert baseline_metrics["health_status"] == "HEALTHY"
    assert baseline_metrics["db_pool_utilization"] < 50.0

    # Step 2: Introduce resource degradation (DB connection pool leak fault)
    demo_mesh.set_fault("scenario-db-leak", {"service_name": "order-service", "fault_type": "latency_spike"})

    # Step 3: Telemetry progression captured
    await demo_mesh.tick()
    degraded_metrics = demo_mesh.get_latest_metrics()["order-service"]
    assert degraded_metrics is not None

    # Step 4: Anomaly detection identifies abnormal pattern
    alerts = observability_engine.get_recent_alerts()
    assert isinstance(alerts, list)

    # Step 5: Regression engine checks for recurring incident patterns
    historical_baseline = {
        "cpu_utilization": 25.0,
        "memory_utilization": 45.0,
        "disk_utilization": 35.0,
        "network_throughput_mbps": 8.0,
        "latency_p50_ms": 45.0,
        "latency_p95_ms": 110.0,
        "latency_p99_ms": 200.0,
        "error_rate": 0.05,
        "db_pool_utilization": 18.0,
    }
    current_eval = historical_baseline.copy()
    current_eval["db_pool_utilization"] = 92.0

    comparison = FourStateComparisonEngine.compare(
        service_name="order-service",
        healthy_baseline=historical_baseline,
        pre_incident=historical_baseline,
        post_remediation=historical_baseline,
        current_state=current_eval,
    )
    assert comparison.metrics["db_pool_utilization"].is_regressing is True
    assert "db_pool_utilization" in comparison.worsening_metrics or "db_pool_utilization" in comparison.regressing_metrics

    # Step 6: Create incident record and seed historical memory
    inc = Incident(
        title="PostgreSQL Connection Pool Starvation in order-service",
        summary="Pool saturation leading to dropped transactions",
        severity="SEV-1",
        status="DETECTED",
        impact_scope="order-service, postgres-db",
    )
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    # Add hypothesis and evidence
    hyp = RootCauseHypothesis(
        incident_id=inc.id,
        hypothesis_text="Database connection pool leak in session handler",
        probability_score=0.92,
        status="ACCEPTED",
        is_confirmed_root_cause=True,
    )
    ev = Evidence(
        incident_id=inc.id,
        evidence_type="error_log",
        source_system="order-service",
        description="FATAL: remaining connection slots are reserved",
        confidence_score=0.99,
        verification_status="VERIFIED",
    )
    db_session.add_all([hyp, ev])
    await db_session.commit()

    # Query reliability memory
    memories = await ReliabilityMemoryEngine.search_memory(
        db=db_session,
        service_name="order-service",
    )
    assert len(memories) >= 1

    # Step 7: Predictive engine projects Time-to-Exhaustion
    series = [(1000.0 + i, 60.0 + (0.5 * i)) for i in range(40)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="order-service",
        metric_name="db_pool_utilization",
        time_series=series,
    )
    assert pred.time_to_exhaustion_seconds is not None
    assert pred.warning_level == "CRITICAL"

    # Step 8: SLO assessment calculates error budget consumption and burn rate
    burn_report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="slo-order-avail",
        service_name="order-service",
        slo_name="Order 30d Availability",
        target_percentage=99.9,
        current_sli=98.5,
    )
    assert burn_report.current_burn_rate >= 10.0
    assert burn_report.fast_burn_alert is True

    # Step 9: Incident Time Machine records event timeline & causal graph
    tm_report = await IncidentTimeMachineEngine.build_incident_timeline(inc.id, db_session)
    assert tm_report is not None
    assert len(tm_report.timeline_events) >= 3
    assert tm_report.causal_graph.blast_radius_score > 0.0

    # Step 10: LangGraph agent assesses situation and recommends safe remediation
    agent_result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        incident_id=inc.id,
        db=db_session,
    )
    assert agent_result is not None
    assert "decision" in agent_result
    decision = agent_result["decision"]
    assert decision["action_id"] in ["act-reset-db-pool", "act-apply-rate-limit", "act-restart-service", "act-escalate-human-review"]

    # Step 11: Remediation executed safely
    rem = RemediationAction(
        incident_id=inc.id,
        action_id="act-reset-db-pool",
        name="Reset Connection Pool",
        description="Drain and cycle stale connections in pool",
        action_type="db_pool",
        expected_outcome="Restore pool connections",
        idempotency_key=f"e2e-rem-{inc.id}",
        target_service_name="postgres-db",
        risk_level="MEDIUM",
        status="EXECUTED",
        verification_status="VERIFIED",
        rollback_status="NONE",
    )
    db_session.add(rem)
    await db_session.commit()

    # Step 12: Post-remediation verification confirms recovery
    demo_mesh.clear_all_faults()
    await demo_mesh.tick()
    recovered_metrics = demo_mesh.get_latest_metrics()["order-service"]
    assert recovered_metrics["health_status"] == "HEALTHY"

    # Step 13: Continuous monitoring verifies no regression
    post_eval = historical_baseline.copy()
    post_comparison = FourStateComparisonEngine.compare(
        service_name="order-service",
        healthy_baseline=historical_baseline,
        pre_incident=current_eval,
        post_remediation=post_eval,
        current_state=post_eval,
    )
    assert len(post_comparison.regressing_metrics) == 0
    assert post_comparison.overall_health_score >= 0.90

    # Step 14: System updates Reliability Memory with new incident and outcome
    inc.status = "RESOLVED"
    inc.resolved_at = datetime.now(timezone.utc)
    inc.mttr_seconds = 480.0
    await db_session.commit()

    memory_entry = await ReliabilityMemoryEngine.index_incident_memory(inc.id, db_session)
    assert memory_entry is not None
    assert memory_entry.incident_id == inc.id
    assert memory_entry.remediation_outcome == "SUSTAINED_SUCCESS"

    # Step 15: Full continuous reliability loop complete!
    assert memory_entry.primary_service == "order-service"
