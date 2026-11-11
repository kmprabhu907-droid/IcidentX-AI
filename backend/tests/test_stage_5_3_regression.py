"""
INCIDENTX AI - Stage 5.3 Regression Detection & Historical Failure Intelligence Tests
Covers all 20 specified validation scenarios for four-state comparison,
multi-feature fingerprinting, similarity metrics, remediation effectiveness,
lifecycle management, and deduplication.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.app.core.database import get_db
from backend.app.models.reliability import RegressionRecord
from backend.app.models.incident import Incident
from backend.app.models.remediation import RemediationAction
from backend.app.services.observability.regression import (
    FourStateComparisonEngine,
    FingerprintBuilder,
    IncidentFingerprint,
    IncidentSimilarityEngine,
    RemediationEffectivenessAnalyzer,
    SRERegressionExplainer,
    RegressionCandidate,
    UnifiedRegressionDetector,
    RegressionLifecycleService,
    normalize_error_string,
)


@pytest.fixture
def baseline_telemetry():
    return {
        "cpu_utilization": 25.0,
        "memory_utilization": 45.0,
        "disk_utilization": 35.0,
        "network_throughput_mbps": 8.0,
        "latency_p50_ms": 45.0,
        "latency_p95_ms": 110.0,
        "latency_p99_ms": 200.0,
        "error_rate": 0.1,
        "db_pool_utilization": 18.0,
        "availability_pct": 99.9,
        "dependency_health": 100.0,
        "request_rate": 12.0,
    }


# 1. Healthy baseline comparison
def test_01_healthy_baseline_comparison(baseline_telemetry):
    comp = FourStateComparisonEngine.compare(
        service_name="order-service",
        healthy_baseline=baseline_telemetry,
        pre_incident=baseline_telemetry,
        post_remediation=baseline_telemetry,
        current_state=baseline_telemetry,
    )
    assert len(comp.regressing_metrics) == 0
    assert len(comp.worsening_metrics) == 0
    assert comp.overall_health_score == 1.0
    assert "stable" in comp.summary.lower()


# 2. Pre-incident versus current comparison
def test_02_pre_incident_vs_current_comparison(baseline_telemetry):
    pre_incident = baseline_telemetry.copy()
    pre_incident["db_pool_utilization"] = 98.0
    pre_incident["error_rate"] = 12.0

    post_remediation = baseline_telemetry.copy()
    current_state = pre_incident.copy()

    comp = FourStateComparisonEngine.compare(
        service_name="postgres-db",
        healthy_baseline=baseline_telemetry,
        pre_incident=pre_incident,
        post_remediation=post_remediation,
        current_state=current_state,
    )
    assert "db_pool_utilization" in comp.regressing_metrics or "db_pool_utilization" in comp.worsening_metrics
    assert "error_rate" in comp.regressing_metrics or "error_rate" in comp.worsening_metrics
    assert comp.overall_health_score < 1.0


# 3. Post-remediation degradation
def test_03_post_remediation_degradation(baseline_telemetry):
    pre = baseline_telemetry.copy()
    pre["latency_p95_ms"] = 1800.0

    post = baseline_telemetry.copy()
    post["latency_p95_ms"] = 120.0

    current = baseline_telemetry.copy()
    current["latency_p95_ms"] = 850.0

    comp = FourStateComparisonEngine.compare(
        service_name="payment-service",
        healthy_baseline=baseline_telemetry,
        pre_incident=pre,
        post_remediation=post,
        current_state=current,
    )
    assert "latency_p95_ms" in comp.regressing_metrics
    mv = comp.metrics["latency_p95_ms"]
    assert mv.is_regressing is True
    assert mv.delta_degradation > 0
    assert mv.recovery_retained_ratio < 1.0


# 4. Recurring database connection exhaustion
def test_04_recurring_database_pool_exhaustion(baseline_telemetry):
    current = baseline_telemetry.copy()
    current["db_pool_utilization"] = 92.0

    pre = baseline_telemetry.copy()
    pre["db_pool_utilization"] = 95.0

    post = baseline_telemetry.copy()
    post["db_pool_utilization"] = 20.0

    candidates = UnifiedRegressionDetector.evaluate_service_regression(
        service_name="postgres-db",
        current_telemetry=current,
        healthy_baseline=baseline_telemetry,
        historical_incident={
            "id": "inc-db-pool-01",
            "title": "PostgreSQL Connection Pool Exhaustion Under Spike",
            "summary": "Database connection pool saturated at 95%",
            "severity": "SEV-1",
        },
        pre_incident_telemetry=pre,
        post_remediation_telemetry=post,
    )
    assert len(candidates) >= 1
    cand = next(c for c in candidates if c.metric_name == "db_pool_utilization")
    assert cand.detected_pattern == "REPEATED_DEPENDENCY_FAILURE"
    assert cand.regression_score >= 0.50


# 5. Recurring memory leak
def test_05_recurring_memory_leak(baseline_telemetry):
    current = baseline_telemetry.copy()
    current["memory_utilization"] = 88.0

    pre = baseline_telemetry.copy()
    pre["memory_utilization"] = 92.0

    post = baseline_telemetry.copy()
    post["memory_utilization"] = 46.0

    candidates = UnifiedRegressionDetector.evaluate_service_regression(
        service_name="order-service",
        current_telemetry=current,
        healthy_baseline=baseline_telemetry,
        historical_incident={
            "id": "inc-mem-01",
            "title": "Order Service Heap Memory Leak",
            "summary": "Unbounded collection growth in cart session cache",
            "severity": "SEV-2",
        },
        pre_incident_telemetry=pre,
        post_remediation_telemetry=post,
    )
    assert len(candidates) >= 1
    cand = next(c for c in candidates if c.metric_name == "memory_utilization")
    assert cand.detected_pattern == "GRADUAL_POST_REMEDIATION_DEGRADATION"


# 6. Similar service but different root cause
def test_06_similar_service_different_root_cause():
    fp_a = FingerprintBuilder.build(
        incident_id="inc-a",
        primary_service="api-gateway",
        telemetry_anomalies={"cpu_utilization": 85.0},
        error_logs=["CPU thermal throttling detected"],
        hypotheses=["High compute utilization in request gzip compression"],
    )
    fp_b = FingerprintBuilder.build(
        incident_id="inc-b",
        primary_service="api-gateway",
        telemetry_anomalies={"latency_p95_ms": 2500.0},
        error_logs=["TLS handshake timeout with client certificate"],
        hypotheses=["Client certificate revocation list CRL lookup delay"],
    )
    sim = IncidentSimilarityEngine.compare_fingerprints(fp_a, fp_b)
    assert sim.root_cause_similarity == 0.0
    assert sim.overall_similarity_score < 0.50


# 7. Incident fingerprint similarity
def test_07_incident_fingerprint_generation():
    fp = FingerprintBuilder.build(
        incident_id="inc-fp-test",
        primary_service="order-service",
        affected_services=["order-service", "payment-service"],
        telemetry_anomalies={"db_pool_utilization": 90.0, "latency_p95_ms": 1500.0},
        error_logs=["connection pool exhausted for db 10.0.1.2:5432 after 15000ms"],
        hypotheses=["Database connection pool timeout in order checkout transaction"],
    )
    assert "order-service" in fp.affected_services
    assert "payment-service" in fp.affected_services
    assert "DATABASE_POOL_EXHAUSTION" in fp.root_cause_categories
    assert len(fp.error_signatures) >= 1
    assert "10.0.1.2" not in list(fp.error_signatures)[0]


# 8. Weighted Jaccard calculations
def test_08_weighted_jaccard_calculation():
    set1 = {"api-gateway", "order-service"}
    set2 = {"api-gateway", "order-service"}
    set3 = {"order-service", "payment-service"}

    assert IncidentSimilarityEngine.weighted_jaccard(set1, set2) == 1.0
    sim = IncidentSimilarityEngine.weighted_jaccard(set1, set3)
    assert round(sim, 2) == 0.33
    assert IncidentSimilarityEngine.weighted_jaccard(set(), set()) == 0.0
    assert IncidentSimilarityEngine.weighted_jaccard(set1, set()) == 0.0


# 9. Cosine similarity
def test_09_cosine_similarity():
    vec_a = {"cpu": 2.0, "memory": 4.0}
    vec_b = {"cpu": 4.0, "memory": 8.0}
    vec_c = {"disk": 5.0}

    assert round(IncidentSimilarityEngine.cosine_similarity(vec_a, vec_b), 3) == 1.0
    assert IncidentSimilarityEngine.cosine_similarity(vec_a, vec_c) == 0.0
    assert IncidentSimilarityEngine.cosine_similarity({}, vec_a) == 0.0


# 10. Dependency graph similarity
def test_10_dependency_graph_similarity():
    graph_a = {"api-gateway": ["order-service"], "order-service": ["postgres-db"]}
    graph_b = {"api-gateway": ["order-service"], "order-service": ["postgres-db"]}
    graph_c = {"auth-service": ["redis-cache"]}

    sim_identical = IncidentSimilarityEngine.dependency_graph_similarity(
        graph_a, graph_b, ["api-gateway", "order-service"], ["api-gateway", "order-service"]
    )
    assert round(sim_identical, 2) == 1.0

    sim_disjoint = IncidentSimilarityEngine.dependency_graph_similarity(
        graph_a, graph_c, ["api-gateway"], ["auth-service"]
    )
    assert sim_disjoint == 0.0


# 11. Missing historical evidence
def test_11_missing_historical_evidence():
    fp_a = FingerprintBuilder.build(incident_id="a", primary_service="auth-service")
    fp_b = FingerprintBuilder.build(incident_id="b", primary_service="order-service")

    sim = IncidentSimilarityEngine.compare_fingerprints(fp_a, fp_b)
    assert sim.metric_vector_similarity == 0.0
    assert sim.root_cause_similarity == 0.0
    assert sim.error_signature_similarity == 0.0


# 12. Insufficient observation windows
def test_12_insufficient_observation_windows(baseline_telemetry):
    report = RemediationEffectivenessAnalyzer.evaluate(
        action_dict={
            "id": "act-restart-1",
            "name": "Restart order-service container",
            "status": "EXECUTED",
            "verification_status": "VERIFIED",
        },
        historical_samples=[],
        current_telemetry={},
        healthy_baseline=baseline_telemetry,
    )
    assert report.outcome == "INSUFFICIENT_EVIDENCE"
    assert report.sample_count == 0


# 13. Sustained remediation success
def test_13_sustained_remediation_success(baseline_telemetry):
    healthy_samples = [
        {"timestamp": "2026-11-11T05:00:00Z", "db_pool_utilization": 18.0},
        {"timestamp": "2026-11-11T05:01:00Z", "db_pool_utilization": 19.0},
        {"timestamp": "2026-11-11T05:02:00Z", "db_pool_utilization": 18.5},
        {"timestamp": "2026-11-11T05:03:00Z", "db_pool_utilization": 17.8},
    ]
    report = RemediationEffectivenessAnalyzer.evaluate(
        action_dict={
            "id": "act-pool-reset",
            "name": "Reset Connection Pool",
            "status": "EXECUTED",
            "verification_status": "VERIFIED",
            "rollback_status": "NONE",
        },
        historical_samples=healthy_samples,
        current_telemetry={"db_pool_utilization": 18.2},
        healthy_baseline=baseline_telemetry,
        target_metric="db_pool_utilization",
    )
    assert report.outcome == "SUSTAINED_SUCCESS"
    assert report.stability_score >= 0.90
    assert len(report.re_abnormal_metrics) == 0


# 14. Temporary remediation success
def test_14_temporary_remediation_success(baseline_telemetry):
    samples = [
        {"timestamp": "2026-11-11T05:00:00Z", "db_pool_utilization": 20.0},
        {"timestamp": "2026-11-11T05:01:00Z", "db_pool_utilization": 22.0},
        {"timestamp": "2026-11-11T05:02:00Z", "db_pool_utilization": 89.0},
    ]
    report = RemediationEffectivenessAnalyzer.evaluate(
        action_dict={
            "id": "act-pool-reset",
            "name": "Reset Connection Pool",
            "status": "EXECUTED",
            "verification_status": "VERIFIED",
            "rollback_status": "NONE",
            "executed_at": "2026-11-11T04:59:00Z",
        },
        historical_samples=samples,
        current_telemetry={"db_pool_utilization": 91.0},
        healthy_baseline=baseline_telemetry,
        target_metric="db_pool_utilization",
    )
    assert report.outcome == "TEMPORARY_SUCCESS"
    assert "db_pool_utilization" in report.re_abnormal_metrics
    assert report.stability_score < 0.50


# 15. Failed remediation history
def test_15_failed_remediation_history(baseline_telemetry):
    report = RemediationEffectivenessAnalyzer.evaluate(
        action_dict={
            "id": "act-bad-action",
            "name": "Apply aggressive thread limit",
            "status": "EXECUTED",
            "verification_status": "FAILED",
            "rollback_status": "ROLLED_BACK",
        },
        historical_samples=[],
        current_telemetry={"cpu_utilization": 90.0},
        healthy_baseline=baseline_telemetry,
    )
    assert report.outcome == "FAILED"
    assert report.required_rollback is True
    assert report.stability_score == 0.0


# 16. Duplicate regression suppression
@pytest.mark.asyncio
async def test_16_duplicate_regression_suppression(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    rec1 = RegressionRecord(
        service_name="order-service",
        metric_name="memory_utilization",
        incident_id="inc-dedup-01",
        baseline_value=45.0,
        post_remediation_value=46.0,
        current_value=85.0,
        regression_score=0.75,
        status="ACTIVE",
        first_observed_at=now,
        last_observed_at=now,
        detected_at=now,
    )
    db_session.add(rec1)
    await db_session.commit()

    from backend.app.services.observability.regression.regression_detector import RegressionCandidate
    cand = RegressionCandidate(
        service_name="order-service",
        metric_name="memory_utilization",
        observed_value=88.0,
        expected_baseline=45.0,
        pre_incident_value=90.0,
        post_remediation_value=46.0,
        regression_score=0.79,
        similarity_score=0.72,
        classification="LIKELY_REGRESSION",
        detected_pattern="GRADUAL_POST_REMEDIATION_DEGRADATION",
        original_incident_id="inc-dedup-01",
    )

    persisted = await RegressionLifecycleService._persist_or_dedup_candidate(cand, db_session)
    await db_session.commit()

    assert persisted.id == rec1.id
    assert persisted.current_value == 88.0
    assert persisted.regression_score == 0.79


# 17. Regression lifecycle updates
@pytest.mark.asyncio
async def test_17_regression_lifecycle_updates(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    rec = RegressionRecord(
        service_name="payment-service",
        metric_name="error_rate",
        baseline_value=0.1,
        post_remediation_value=0.2,
        current_value=8.5,
        regression_score=0.82,
        status="ACTIVE",
        first_observed_at=now,
        last_observed_at=now,
        detected_at=now,
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)

    updated = await RegressionLifecycleService.update_status(rec.id, "CONFIRMED", db_session)
    assert updated["status"] == "CONFIRMED"

    updated = await RegressionLifecycleService.update_status(rec.id, "RESOLVED", db_session)
    assert updated["status"] == "RESOLVED"

    with pytest.raises(ValueError):
        await RegressionLifecycleService.update_status(rec.id, "INVALID_STATE", db_session)


# 18. API filters and pagination
@pytest.mark.asyncio
async def test_18_api_filters_and_pagination(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/observability/regressions?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data
        assert "page" in data
        assert "page_size" in data

        act_resp = await client.get("/api/v1/observability/regressions/active")
        assert act_resp.status_code == 200
        assert isinstance(act_resp.json(), list)


# 19. Data source separation
def test_19_data_source_separation():
    cand_sim = RegressionCandidate(
        service_name="api-gateway",
        metric_name="latency_p95_ms",
        observed_value=500.0,
        expected_baseline=110.0,
        pre_incident_value=600.0,
        post_remediation_value=120.0,
        regression_score=0.70,
        similarity_score=0.65,
        classification="LIKELY_REGRESSION",
        detected_pattern="SAME_FAILURE_RECURRING",
        original_incident_id="inc-1",
        data_source="SIMULATED",
    )
    assert cand_sim.data_source == "SIMULATED"
    cand_dict = cand_sim.to_dict()
    assert cand_dict["data_source"] == "SIMULATED"


# 20. Ten SRE diagnostic answers
def test_20_ten_sre_diagnostic_answers():
    explanation = SRERegressionExplainer.explain(
        current_service="order-service",
        current_metric="db_pool_utilization",
        observed_value=94.0,
        expected_baseline=18.0,
        post_remediation_value=20.0,
        historical_incident={
            "id": "inc-hist-12345",
            "title": "Black Friday Connection Pool Collapse",
            "summary": "Database connection pool saturated under peak checkout transactions",
        },
        similarity_data={
            "overall_similarity_score": 0.88,
            "services_similarity": 1.0,
            "metric_vector_similarity": 0.95,
            "root_cause_similarity": 0.90,
        },
        remediation_data={
            "name": "Reset DB Connection Pool",
            "outcome": "TEMPORARY_SUCCESS",
        },
        regression_score=0.85,
        classification="CONFIRMED_REGRESSION",
    )
    d = explanation.to_dict()
    assert len(d) == 10
    assert "Black Friday Connection Pool Collapse" in d["which_previous_incident"]
    assert "order-service" in d["affected_services"]
    assert "db_pool_utilization" in d["metrics_returning_abnormal"]
    assert "Database connection pool saturated" in d["original_root_cause_hypothesis"]
    assert "Reset DB Connection Pool" in d["previous_remediation_performed"]
    assert len(d["did_remediation_provide_sustained_improvement"]) > 0
    assert len(d["evidence_supporting_recurrence"]) > 0
    assert len(d["evidence_contradicting_recurrence"]) > 0
    assert "88.0%" in d["similarity_strength"]
    assert len(d["next_investigation_step"]) > 0
