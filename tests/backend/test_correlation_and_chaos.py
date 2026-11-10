"""
INCIDENTX AI - Correlation Engine and Chaos Controller Unit Tests
"""

import pytest
from backend.app.services.observability.correlation import CorrelationEngine
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)
from backend.app.services.simulation.chaos_controller import ChaosController


def test_correlation_engine_root_cause_and_clustering():
    engine = CorrelationEngine(cooldown_seconds=120)

    # Cascading alerts from DB exhaustion: postgres-db, order-service, api-gateway
    alerts = [
        AnomalyAlert(
            detector_type=DetectorType.STATIC_THRESHOLD,
            service_name="postgres-db",
            metric_name="db_pool_utilization",
            current_value=100.0,
            threshold_or_baseline=90.0,
            severity=AlertSeverity.CRITICAL,
            message="postgres-db pool exhausted",
        ),
        AnomalyAlert(
            detector_type=DetectorType.ERROR_INTELLIGENCE,
            service_name="order-service",
            metric_name="error_rate",
            current_value=65.0,
            threshold_or_baseline=15.0,
            severity=AlertSeverity.CRITICAL,
            message="order-service error spike",
        ),
        AnomalyAlert(
            detector_type=DetectorType.STATIC_THRESHOLD,
            service_name="api-gateway",
            metric_name="error_rate",
            current_value=45.0,
            threshold_or_baseline=15.0,
            severity=AlertSeverity.CRITICAL,
            message="api-gateway error spike",
        ),
    ]

    candidates = engine.correlate(alerts)
    assert len(candidates) == 1
    c = candidates[0]

    # Must accurately pinpoint postgres-db as root culprit, NOT api-gateway
    assert c.culprit_service == "postgres-db"
    assert c.severity == "SEV-1"
    assert "postgres-db" in c.impacted_services
    assert "order-service" in c.impacted_services
    assert "api-gateway" in c.impacted_services
    assert len(c.evidence_items) > 0
    assert c.confidence_score >= 0.90

    # Test deduplication: feeding alerts again within cooldown window returns 0 new incidents
    dup_candidates = engine.correlate(alerts)
    assert len(dup_candidates) == 0


@pytest.mark.asyncio
async def test_chaos_controller_lifecycle():
    controller = ChaosController()

    # 1. Verify 9 scenarios
    scenarios = controller.list_scenarios()
    assert len(scenarios) == 9
    scenario_ids = {s["id"] for s in scenarios}
    assert "payment_latency" in scenario_ids
    assert "db_pool_exhaustion" in scenario_ids
    assert "cpu_spike" in scenario_ids
    assert "memory_leak" in scenario_ids
    assert "redis_down" in scenario_ids
    assert "http_500_cascade" in scenario_ids
    assert "traffic_surge" in scenario_ids
    assert "instance_termination" in scenario_ids
    assert "deployment_regression" in scenario_ids

    # 2. Inject fault
    res = await controller.inject(
        scenario_id="payment_latency",
        target_service="payment-service",
        duration_seconds=30,
        parameters={"latency_ms": 2500.0},
    )
    assert res["scenario_id"] == "payment_latency"
    assert res["data_source"] == "SIMULATED"

    # Status check
    status = controller.get_status()
    assert status["is_active"] is True
    assert status["active_fault_count"] == 1
    assert status["data_source"] == "SIMULATED"

    # 3. Terminate fault
    stopped = await controller.stop("payment_latency")
    assert stopped is True

    # Emergency stop all on empty
    stopped_count = await controller.stop_all()
    assert stopped_count == 0
    assert controller.get_status()["is_active"] is False
