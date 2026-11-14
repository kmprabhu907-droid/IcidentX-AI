"""
INCIDENTX AI - Phase 15 Comprehensive Test Suite (Predictive SRE Intelligence)
"""

import pytest
from backend.app.services.sre_intelligence.schemas import (
    AnomalyClassification,
    RiskCategory,
    ServiceHealthStatus,
)
from backend.app.services.sre_intelligence.sre_engine import SREIntelligenceEngine


def test_anomaly_detection_z_score():
    engine = SREIntelligenceEngine()
    
    # Normal metrics
    normal = engine.detect_anomalies("payment-service", {
        "cpu_percent": 36.0,
        "memory_percent": 46.0,
        "p95_latency_ms": 70.0,
        "error_rate_percent": 0.04,
    })
    assert normal.overall_classification == AnomalyClassification.NORMAL
    assert normal.multivariate_anomaly_score < 0.3

    # Severe anomalous metrics
    anomalous = engine.detect_anomalies("payment-service", {
        "cpu_percent": 96.0,          # 7.6 std dev away
        "memory_percent": 95.0,       # 8.3 std dev away
        "p95_latency_ms": 1850.0,     # >100 std dev away
        "error_rate_percent": 24.5,
    })
    assert anomalous.overall_classification == AnomalyClassification.CONFIRMED_ANOMALY
    assert anomalous.multivariate_anomaly_score >= 0.70


def test_incident_prediction_early_warning():
    engine = SREIntelligenceEngine()
    
    # Memory exhaustion projection
    preds = engine.predict_incidents("payment-service", {
        "memory_percent": 88.0,
        "pod_restart_count": 2.0,
    })
    assert len(preds) >= 1
    mem_pred = next(p for p in preds if p.risk_type == "MEMORY_EXHAUSTION")
    assert mem_pred.risk_category in (RiskCategory.HIGH, RiskCategory.CRITICAL)
    assert mem_pred.confidence_score > 0.85
    assert mem_pred.predicted_lead_time_minutes > 0


def test_service_health_and_slos():
    engine = SREIntelligenceEngine()
    
    # Healthy service
    health = engine.evaluate_service_health("payment-service", {
        "error_rate_percent": 0.01,
        "p95_latency_ms": 40.0,
    })
    assert health.health_status == ServiceHealthStatus.HEALTHY
    assert health.availability_percent >= 99.9

    # Degraded service
    degraded = engine.evaluate_service_health("payment-service", {
        "error_rate_percent": 6.5,
        "p95_latency_ms": 1200.0,
    })
    assert degraded.health_status == ServiceHealthStatus.CRITICAL

    # SLO targets & burn rate
    slos = engine.get_slo_targets("payment-service", error_rate=2.5)
    assert len(slos) == 2
    assert slos[0].burn_rate_status == "CRITICAL_BURN"
    assert slos[0].burn_rate >= 14.0


def test_deployment_risk_and_cascading():
    engine = SREIntelligenceEngine()
    
    # Deployment correlation
    dep = engine.correlate_deployment(
        service_name="payment-service",
        git_sha="sha-9b2f11",
        deployed_minutes_ago=10.0,
        error_rate=4.2,
    )
    assert dep.is_correlated_with_degradation is True
    assert dep.risk_category == RiskCategory.CRITICAL

    # Cascading failure risk
    cascade = engine.evaluate_cascading_risk("payment-service")
    assert "order-service" in cascade.downstream_impacted_services
    assert cascade.blast_radius_score >= 0.70


def test_predictive_recommendations_and_evaluation():
    engine = SREIntelligenceEngine()
    preds = engine.predict_incidents("payment-service", {"memory_percent": 82.0})
    recs = engine.get_proactive_recommendations("payment-service", preds)
    assert len(recs) >= 1
    assert "memory" in recs[0].suggested_action.lower()

    # Evaluation
    eval_metrics = engine.get_model_evaluation()
    assert eval_metrics.anomaly_precision >= 0.90
    assert eval_metrics.prediction_accuracy >= 0.85
