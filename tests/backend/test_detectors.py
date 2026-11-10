"""
INCIDENTX AI - Anomaly Detection Modules Unit Tests
Validates all 5 detection engines:
1. Static Threshold Detector
2. Baseline Statistical Detector (3-sigma)
3. Latency Tail & Percentile Detector
4. Error Intelligence & Exception Cluster Detector
5. Traffic Intelligence Detector
"""

import pytest
from backend.app.services.observability.detectors.baseline import BaselineDetector
from backend.app.services.observability.detectors.error import ErrorIntelligenceDetector
from backend.app.services.observability.detectors.latency import LatencyDetector
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    DetectorType,
)
from backend.app.services.observability.detectors.threshold import StaticThresholdDetector
from backend.app.services.observability.detectors.traffic import TrafficIntelligenceDetector


def test_static_threshold_detector():
    detector = StaticThresholdDetector()

    # Normal healthy metrics
    normal_snapshot = {
        "service_name": "order-service",
        "cpu_utilization": 45.0,
        "memory_utilization": 50.0,
        "error_rate": 0.5,
        "latency_p95_ms": 120.0,
        "db_pool_utilization": 20.0,
    }
    alerts = detector.evaluate(normal_snapshot)
    assert len(alerts) == 0

    # Warning breach
    warn_snapshot = {
        "service_name": "order-service",
        "cpu_utilization": 82.0,  # warn > 80%
        "error_rate": 6.0,        # warn > 5%
    }
    alerts = detector.evaluate(warn_snapshot)
    assert len(alerts) == 2
    assert all(a.severity == AlertSeverity.WARN for a in alerts)

    # Critical breach
    crit_snapshot = {
        "service_name": "postgres-db",
        "cpu_utilization": 94.0,       # crit > 90%
        "db_pool_utilization": 98.0,   # crit > 90%
        "latency_p95_ms": 2200.0,      # crit > 1500ms
    }
    alerts = detector.evaluate(crit_snapshot)
    assert len(alerts) == 3
    assert all(a.severity == AlertSeverity.CRITICAL for a in alerts)


def test_baseline_detector():
    detector = BaselineDetector(min_samples=10, z_score_threshold=3.0)

    # Insufficient history
    short_history = [{"latency_p95_ms": 100.0} for _ in range(5)]
    alerts = detector.evaluate({"service_name": "order-service", "latency_p95_ms": 500.0}, short_history)
    assert len(alerts) == 0

    # Stable baseline around 100ms
    stable_history = [{"latency_p95_ms": 100.0 + (i % 3)} for i in range(20)]

    # Normal value
    normal_snapshot = {"service_name": "order-service", "latency_p95_ms": 104.0}
    assert len(detector.evaluate(normal_snapshot, stable_history)) == 0

    # Extreme deviation (z-score > 3.0)
    spike_snapshot = {"service_name": "order-service", "latency_p95_ms": 350.0}
    alerts = detector.evaluate(spike_snapshot, stable_history)
    assert len(alerts) == 1
    assert alerts[0].detector_type == DetectorType.BASELINE_DEVIATION
    assert alerts[0].deviation_sigma is not None
    assert alerts[0].deviation_sigma >= 3.0


def test_latency_detector():
    detector = LatencyDetector()

    # Normal latency profile
    healthy = {
        "service_name": "api-gateway",
        "latency_p50_ms": 25.0,
        "latency_p95_ms": 70.0,
        "latency_p99_ms": 120.0,
    }
    assert len(detector.evaluate(healthy)) == 0

    # Tail divergence (P99 is 10x of P50)
    tail_diverged = {
        "service_name": "payment-service",
        "latency_p50_ms": 30.0,
        "latency_p95_ms": 200.0,
        "latency_p99_ms": 600.0,
    }
    alerts = detector.evaluate(tail_diverged)
    assert any(a.metric_name == "tail_divergence_ratio" for a in alerts)

    # Critical P99 latency spike > 2000ms
    crit_tail = {
        "service_name": "payment-service",
        "latency_p50_ms": 150.0,
        "latency_p95_ms": 1800.0,
        "latency_p99_ms": 2800.0,
    }
    alerts = detector.evaluate(crit_tail)
    assert any(a.severity == AlertSeverity.CRITICAL and a.metric_name == "latency_p99_ms" for a in alerts)


def test_error_intelligence_detector():
    detector = ErrorIntelligenceDetector()

    # Metric error rate evaluation
    crit_snapshot = {"service_name": "order-service", "error_rate": 35.0}
    alerts = detector.evaluate_metrics(crit_snapshot)
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL

    # Rapid error acceleration
    prev = {"service_name": "order-service", "error_rate": 2.0}
    curr = {"service_name": "order-service", "error_rate": 12.0}
    accel_alerts = detector.evaluate_metrics(curr, prev)
    assert any(a.metric_name == "error_rate_velocity" for a in accel_alerts)

    # Log exception clustering
    sample_logs = [
        {"service_name": "order-service", "level": "ERROR", "message": "ConnectionPoolTimeout: timeout after 3000ms"},
        {"service_name": "order-service", "level": "ERROR", "message": "ConnectionPoolTimeout: timeout after 3000ms"},
        {"service_name": "order-service", "level": "ERROR", "message": "ConnectionPoolTimeout: timeout after 3000ms"},
        {"service_name": "auth-service", "level": "INFO", "message": "Token verified"},
    ]
    log_alerts = detector.evaluate_logs(sample_logs)
    assert len(log_alerts) == 1
    assert log_alerts[0].service_name == "order-service"
    assert "ConnectionPoolTimeout" in log_alerts[0].message


def test_traffic_intelligence_detector():
    detector = TrafficIntelligenceDetector()
    base_rps = 20.0

    # Normal traffic
    normal = {"service_name": "api-gateway", "request_rate": 22.0}
    assert len(detector.evaluate(normal, base_rps)) == 0

    # Traffic surge (3x base)
    surge = {"service_name": "api-gateway", "request_rate": 65.0}
    surge_alerts = detector.evaluate(surge, base_rps)
    assert len(surge_alerts) == 1
    assert surge_alerts[0].metric_name == "traffic_surge"

    # Traffic blackout (dropped to near zero)
    blackout = {"service_name": "api-gateway", "request_rate": 1.0}
    blackout_alerts = detector.evaluate(blackout, base_rps)
    assert len(blackout_alerts) == 1
    assert blackout_alerts[0].metric_name == "traffic_blackout"
