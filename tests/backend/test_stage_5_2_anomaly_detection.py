"""
INCIDENTX AI - Stage 5.2 Advanced Anomaly & Resource-Creep Detection Test Suite
Validates dynamic baselines, contamination prevention, EWMA smoothing, linear trend regression,
confidence scoring, multi-signal correlation, deduplication, lifecycle status, and API endpoints.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from backend.app.core.database import async_session_factory
from backend.app.models.reliability import AnomalyRecord
from backend.app.services.observability.anomaly import (
    AnomalyConfidenceCalculator,
    AnomalyLifecycleService,
    AnomalySeverity,
    DynamicBaselineEngine,
    EWMAEngine,
    ResourceCreepDetector,
    UnifiedAnomalyDetector,
    anomaly_service,
    classify_anomaly_severity,
)
from backend.main import app


@pytest.fixture(autouse=True)
async def clean_anomaly_records():
    """Clean up test anomaly records after test runs."""
    yield
    async with async_session_factory() as session:
        await session.execute(delete(AnomalyRecord).where(AnomalyRecord.service_name.like("test-%")))
        await session.commit()


@pytest.mark.asyncio
async def test_01_normal_stable_cpu_behaviour():
    """Test 1: Verify normal, stable CPU within baseline does NOT trigger false positive anomalies."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-stable-svc"

    # Seed baseline with normal values around 25% CPU
    for _ in range(20):
        detector.baseline_engine.add_observation(service_name, "cpu_utilization", 25.0)

    # Evaluate normal observation at 25.5%
    metrics = {
        "service_id": "test-svc-1",
        "service_name": service_name,
        "cpu_utilization": 25.5,
        "memory_utilization": 40.0,
        "disk_utilization": 30.0,
        "error_rate": 0.05,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-1", service_name, metrics)
    cpu_candidates = [c for c in candidates if c.metric_name == "cpu_utilization"]
    assert len(cpu_candidates) == 0, "Stable CPU should not trigger anomaly"


@pytest.mark.asyncio
async def test_02_sudden_cpu_spike():
    """Test 2: Verify sudden severe CPU jump triggers a high/critical anomaly."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-spike-svc"

    # Baseline at 20%
    for _ in range(20):
        detector.baseline_engine.add_observation(service_name, "cpu_utilization", 20.0)

    # Sudden spike to 96%
    metrics = {
        "service_id": "test-svc-2",
        "service_name": service_name,
        "cpu_utilization": 96.0,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-2", service_name, metrics)
    cpu_anomalies = [c for c in candidates if c.metric_name == "cpu_utilization"]
    assert len(cpu_anomalies) >= 1
    assert cpu_anomalies[0].severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]
    assert cpu_anomalies[0].observed_value == 96.0


@pytest.mark.asyncio
async def test_03_gradual_memory_leak():
    """Test 3: Verify progressive linear memory growth triggers RESOURCE_CREEP_OLS anomaly."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-leak-svc"
    now = datetime.now(timezone.utc)

    # Seed memory leak with steady upward slope (1% growth per second over 30s)
    for i in range(30):
        t = now - timedelta(seconds=(30 - i))
        val = 50.0 + (i * 1.0)
        detector.creep_detector.add_sample(service_name, "memory_utilization", val, timestamp=t)
        detector.baseline_engine.add_observation(service_name, "memory_utilization", 50.0)

    # Evaluate current sample at 81%
    metrics = {
        "service_id": "test-svc-3",
        "service_name": service_name,
        "memory_utilization": 81.0,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-3", service_name, metrics)
    mem_candidates = [c for c in candidates if c.metric_name == "memory_utilization"]

    assert len(mem_candidates) >= 1
    c = mem_candidates[0]
    assert c.detector_type == "RESOURCE_CREEP_OLS"
    assert c.trend_slope is not None and c.trend_slope > 0.0
    assert "creep_analysis" in c.supporting_evidence
    assert c.supporting_evidence["creep_analysis"]["r_squared"] >= 0.65


@pytest.mark.asyncio
async def test_04_gradual_db_connection_pool_exhaustion():
    """Test 4: Verify gradual DB pool creep calculates slope, rate/min, and TTE."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-db-pool-svc"
    now = datetime.now(timezone.utc)

    for i in range(25):
        t = now - timedelta(seconds=(25 - i))
        val = 40.0 + (i * 1.2)
        detector.creep_detector.add_sample(service_name, "db_pool_utilization", val, timestamp=t)
        detector.baseline_engine.add_observation(service_name, "db_pool_utilization", 35.0)

    metrics = {
        "service_id": "test-svc-4",
        "service_name": service_name,
        "db_pool_utilization": 72.0,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-4", service_name, metrics)
    pool_anomalies = [c for c in candidates if c.metric_name == "db_pool_utilization"]

    assert len(pool_anomalies) >= 1
    p = pool_anomalies[0]
    assert p.trend_slope is not None and p.trend_slope > 0.0
    assert p.supporting_evidence["creep_analysis"]["rate_per_minute"] > 0.0


@pytest.mark.asyncio
async def test_05_disk_utilization_growth():
    """Test 5: Verify disk utilization creep detection."""
    creep = ResourceCreepDetector(window_size=30, min_samples=10, min_r_squared=0.6)
    service_name = "test-disk-svc"
    now = datetime.now(timezone.utc)

    for i in range(20):
        t = now - timedelta(seconds=(20 - i))
        val = 60.0 + (i * 0.5)
        creep.add_sample(service_name, "disk_utilization", val, timestamp=t)

    eval_result = creep.evaluate_creep(service_name, "disk_utilization", current_value=70.0)
    assert eval_result is not None
    assert eval_result["is_creep"] is True
    assert eval_result["slope"] > 0.0
    assert eval_result["r_squared"] >= 0.6


@pytest.mark.asyncio
async def test_06_latency_degradation():
    """Test 6: Verify latency tail inflation is detected."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-latency-svc"

    # Baseline around 30ms
    for _ in range(20):
        detector.baseline_engine.add_observation(service_name, "latency_p95_ms", 30.0)

    metrics = {
        "service_id": "test-svc-6",
        "service_name": service_name,
        "latency_p95_ms": 450.0,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-6", service_name, metrics)
    lat_anomalies = [c for c in candidates if c.metric_name == "latency_p95_ms"]
    assert len(lat_anomalies) >= 1
    assert lat_anomalies[0].deviation > 300.0


@pytest.mark.asyncio
async def test_07_error_rate_anomaly():
    """Test 7: Verify elevated error rate detection."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-error-svc"

    for _ in range(20):
        detector.baseline_engine.add_observation(service_name, "error_rate", 0.05)

    metrics = {
        "service_id": "test-svc-7",
        "service_name": service_name,
        "error_rate": 15.5,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-7", service_name, metrics)
    err_anomalies = [c for c in candidates if c.metric_name == "error_rate"]
    assert len(err_anomalies) >= 1
    assert err_anomalies[0].severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]


@pytest.mark.asyncio
async def test_08_ewma_calculations():
    """Test 8: Verify EWMA smoothing formula: EWMA(t) = a * X(t) + (1-a) * EWMA(t-1)."""
    engine = EWMAEngine()
    s = "test-ewma-svc"
    m = "cpu_utilization"

    # Initial value
    e1 = engine.update(s, m, 10.0)
    assert e1 == 10.0

    # Next value: alpha=0.2 (from rules for CPU) -> 0.2*50 + 0.8*10 = 10 + 8 = 18.0
    e2 = engine.update(s, m, 50.0)
    assert e2 == 18.0

    # Next value: 0.2*50 + 0.8*18 = 10 + 14.4 = 24.4
    e3 = engine.update(s, m, 50.0)
    assert e3 == 24.4


@pytest.mark.asyncio
async def test_09_baseline_adaptation():
    """Test 9: Verify baseline mean and std dev adapt with new clean observations."""
    engine = DynamicBaselineEngine(window_size=20, min_samples=5)
    s = "test-adapt-svc"
    m = "cpu_utilization"

    for v in [10.0, 12.0, 11.0, 13.0, 10.0]:
        accepted = engine.add_observation(s, m, v)
        assert accepted is True

    base = engine.get_baseline(s, m)
    assert base.has_sufficient_history is True
    assert 10.5 <= base.mean <= 12.0
    assert base.sample_count == 5


@pytest.mark.asyncio
async def test_10_baseline_contamination_prevention():
    """Test 10: Verify severe outlier / known anomaly is rejected from contaminating clean baseline."""
    engine = DynamicBaselineEngine(window_size=20, min_samples=10)
    s = "test-contam-svc"
    m = "cpu_utilization"

    # Seed baseline with 10 values at 20%
    for _ in range(10):
        engine.add_observation(s, m, 20.0)

    # 1. Attempt to add a 99% outlier: should be rejected
    accepted_outlier = engine.add_observation(s, m, 99.0)
    assert accepted_outlier is False

    # 2. Attempt to add explicit known anomaly: should be rejected
    accepted_flagged = engine.add_observation(s, m, 25.0, is_known_anomaly=True)
    assert accepted_flagged is False

    # Baseline remains uncontaminated at 20.0
    base = engine.get_baseline(s, m)
    assert base.mean == 20.0


@pytest.mark.asyncio
async def test_11_confidence_scoring():
    """Test 11: Verify confidence scoring breakdown in [0.0, 1.0]."""
    score_data = AnomalyConfidenceCalculator.calculate(
        z_score=4.5,
        consecutive_observations=4,
        baseline_std_dev=2.0,
        baseline_mean=25.0,
        trend_r_squared=0.85,
        corroborating_signals_count=2,
        sample_count=25,
    )
    conf = score_data["confidence"]
    assert 0.0 <= conf <= 1.0
    assert conf >= 0.75  # High confidence under strong evidence
    assert "magnitude_score" in score_data["components"]
    assert "persistence_score" in score_data["components"]
    assert "corroborating_score" in score_data["components"]


@pytest.mark.asyncio
async def test_12_severity_classification():
    """Test 12: Verify deterministic severity classification rules."""
    # Critical threshold breach
    sev1 = classify_anomaly_severity(
        metric_name="error_rate",
        observed_value=25.0,  # Critical threshold is 10.0
        baseline_value=0.1,
        z_score=6.0,
        is_creep=False,
        corroborating_count=1,
        confidence=0.9,
    )
    assert sev1 == AnomalySeverity.CRITICAL

    # Mild deviation
    sev2 = classify_anomaly_severity(
        metric_name="cpu_utilization",
        observed_value=35.0,
        baseline_value=20.0,
        z_score=2.2,
        is_creep=False,
        corroborating_count=0,
        confidence=0.5,
    )
    assert sev2 in [AnomalySeverity.LOW, AnomalySeverity.INFO]


@pytest.mark.asyncio
async def test_13_correlated_multi_signal_detection():
    """Test 13: Verify multi-signal correlation identifies cluster explanation."""
    detector = UnifiedAnomalyDetector()
    service_name = "test-corrob-svc"

    # Baseline
    for _ in range(15):
        detector.baseline_engine.add_observation(service_name, "memory_utilization", 40.0)
        detector.baseline_engine.add_observation(service_name, "latency_p95_ms", 30.0)
        detector.baseline_engine.add_observation(service_name, "cpu_utilization", 20.0)

    # Coincident memory + latency + cpu spike
    metrics = {
        "service_id": "test-svc-13",
        "service_name": service_name,
        "memory_utilization": 88.0,
        "latency_p95_ms": 850.0,
        "cpu_utilization": 85.0,
    }
    candidates = detector.evaluate_service_snapshot("test-svc-13", service_name, metrics)
    mem_anom = next(c for c in candidates if c.metric_name == "memory_utilization")

    corrob = mem_anom.supporting_evidence["corroborating_signals"]
    assert "latency_p95_ms" in corrob or "cpu_utilization" in corrob
    assert "Memory Leak" in mem_anom.supporting_evidence.get("cluster_name", "") or "memory" in mem_anom.supporting_evidence.get("cluster_explanation", "").lower()


@pytest.mark.asyncio
async def test_14_insufficient_historical_data():
    """Test 14: Handles services with < 10 samples gracefully using fallback."""
    engine = DynamicBaselineEngine(min_samples=10)
    s = "test-new-svc"
    m = "cpu_utilization"

    # Only 2 samples
    engine.add_observation(s, m, 22.0)
    engine.add_observation(s, m, 24.0)

    base = engine.get_baseline(s, m)
    assert base.has_sufficient_history is False
    assert base.sample_count == 2


@pytest.mark.asyncio
async def test_15_missing_telemetry():
    """Test 15: Handles missing metrics in payload without crashing."""
    detector = UnifiedAnomalyDetector()
    candidates = detector.evaluate_service_snapshot("test-empty-svc", "test-empty-svc", {})
    assert len(candidates) == 0


@pytest.mark.asyncio
async def test_16_invalid_telemetry():
    """Test 16: Handles None, NaN, and string garbage without error."""
    engine = DynamicBaselineEngine()
    assert engine.add_observation("test-inv", "cpu_utilization", None) is False
    assert engine.add_observation("test-inv", "cpu_utilization", float("nan")) is False
    assert engine.add_observation("test-inv", "cpu_utilization", "garbage") is False


@pytest.mark.asyncio
async def test_17_duplicate_alert_suppression():
    """Test 17: Consecutive identical anomalies update existing record rather than inserting new rows."""
    svc = AnomalyLifecycleService()
    service_name = "test-dedup-svc"

    # Pre-seed baseline
    for _ in range(15):
        svc.detector.baseline_engine.add_observation(service_name, "cpu_utilization", 20.0)

    # First cycle with CPU spike
    metrics = {
        "service_id": "test-svc-17",
        "service_name": service_name,
        "cpu_utilization": 95.0,
    }
    c1 = svc.detector.evaluate_service_snapshot("test-svc-17", service_name, metrics)
    now1 = datetime.now(timezone.utc)
    res1 = await svc._persist_and_deduplicate(c1, now1)
    assert len(res1) == 1

    # Second cycle with ongoing CPU spike
    now2 = now1 + timedelta(seconds=5)
    c2 = svc.detector.evaluate_service_snapshot("test-svc-17", service_name, metrics)
    res2 = await svc._persist_and_deduplicate(c2, now2)
    assert len(res2) == 1

    # Verify only ONE row exists in database and observation_count == 2
    async with async_session_factory() as session:
        stmt = select(AnomalyRecord).where(
            AnomalyRecord.service_name == service_name,
            AnomalyRecord.metric_name == "cpu_utilization",
        )
        records = (await session.execute(stmt)).scalars().all()
        assert len(records) == 1
        assert records[0].observation_count == 2
        assert records[0].status == "ACTIVE"


@pytest.mark.asyncio
async def test_18_anomaly_lifecycle_updates():
    """Test 18: Verify transitioning anomaly status (ACTIVE -> ACKNOWLEDGED -> RESOLVED)."""
    svc = AnomalyLifecycleService()
    now = datetime.now(timezone.utc)

    # Insert an active record
    async with async_session_factory() as session:
        rec = AnomalyRecord(
            service_name="test-lifecycle-svc",
            metric_name="memory_utilization",
            observed_value=85.0,
            expected_baseline=40.0,
            deviation=45.0,
            severity="HIGH",
            confidence=0.88,
            detector_type="RESOURCE_CREEP_OLS",
            status="ACTIVE",
            detected_at=now,
        )
        session.add(rec)
        await session.commit()
        record_id = rec.id

    # 1. Acknowledge
    ack = await svc.update_anomaly_status(record_id, "ACKNOWLEDGED")
    assert ack is not None
    assert ack["status"] == "ACKNOWLEDGED"

    # 2. Resolve
    res = await svc.update_anomaly_status(record_id, "RESOLVED")
    assert res is not None
    assert res["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_19_api_filtering_and_pagination():
    """Test 19: Test /api/v1/observability/anomalies endpoint filtering and pagination."""
    now = datetime.now(timezone.utc)

    # Seed 3 records
    async with async_session_factory() as session:
        a1 = AnomalyRecord(
            service_name="test-api-svc-a",
            metric_name="cpu_utilization",
            observed_value=90.0,
            expected_baseline=20.0,
            deviation=70.0,
            severity="CRITICAL",
            confidence=0.95,
            detector_type="DYNAMIC_BASELINE_3SIGMA",
            status="ACTIVE",
            detected_at=now,
        )
        a2 = AnomalyRecord(
            service_name="test-api-svc-b",
            metric_name="error_rate",
            observed_value=12.0,
            expected_baseline=0.1,
            deviation=11.9,
            severity="MEDIUM",
            confidence=0.85,
            detector_type="DYNAMIC_BASELINE_3SIGMA",
            status="ACTIVE",
            detected_at=now,
        )
        session.add_all([a1, a2])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Filter by service_name
        r1 = await client.get("/api/v1/observability/anomalies", params={"service_name": "test-api-svc-a"})
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["total"] >= 1
        assert d1["items"][0]["service_name"] == "test-api-svc-a"

        # Filter by severity
        r2 = await client.get("/api/v1/observability/anomalies", params={"severity": "CRITICAL"})
        assert r2.status_code == 200
        d2 = r2.json()
        assert all(item["severity"] == "CRITICAL" for item in d2["items"])

        # Status endpoint
        r3 = await client.get("/api/v1/observability/detection/status")
        assert r3.status_code == 200
        assert r3.json()["status"] in ["HEALTHY", "DEGRADED"]

        # Baselines endpoint
        r4 = await client.get("/api/v1/observability/baselines/order-service")
        assert r4.status_code == 200
        d4 = r4.json()
        assert "baselines" in d4
        assert "cpu_utilization" in d4["baselines"]


@pytest.mark.asyncio
async def test_20_active_anomalies_endpoint():
    """Test 20: Test /api/v1/observability/anomalies/active endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/observability/anomalies/active")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
