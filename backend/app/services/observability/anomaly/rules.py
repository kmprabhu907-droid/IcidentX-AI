"""
INCIDENTX AI - Anomaly Rules, Thresholds & Multi-Signal Correlation Matrix
Defines metric baseline constraints, critical operating thresholds, correlation clusters,
and deterministic severity classification policies.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


# Metric bounds and nominal operating limits
METRIC_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    "cpu_utilization": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 80.0,
        "critical_threshold": 92.0,
        "ewma_alpha": 0.2,
        "creep_slope_min": 0.05,  # % per second
    },
    "memory_utilization": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 80.0,
        "critical_threshold": 90.0,
        "ewma_alpha": 0.1,  # smooth resource tracking
        "creep_slope_min": 0.03,  # persistent leak
    },
    "disk_utilization": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 75.0,
        "critical_threshold": 88.0,
        "ewma_alpha": 0.05,
        "creep_slope_min": 0.02,
    },
    "network_throughput_mbps": {
        "unit": "MB/s",
        "min_possible": 0.0,
        "max_possible": 500.0,
        "warn_threshold": 45.0,
        "critical_threshold": 100.0,
        "ewma_alpha": 0.3,
        "creep_slope_min": 0.1,
    },
    "latency_p50_ms": {
        "unit": "ms",
        "min_possible": 0.5,
        "max_possible": 60000.0,
        "warn_threshold": 150.0,
        "critical_threshold": 500.0,
        "ewma_alpha": 0.3,
        "creep_slope_min": 1.0,
    },
    "latency_p95_ms": {
        "unit": "ms",
        "min_possible": 1.0,
        "max_possible": 60000.0,
        "warn_threshold": 300.0,
        "critical_threshold": 1200.0,
        "ewma_alpha": 0.3,
        "creep_slope_min": 2.5,
    },
    "latency_p99_ms": {
        "unit": "ms",
        "min_possible": 2.0,
        "max_possible": 60000.0,
        "warn_threshold": 600.0,
        "critical_threshold": 2500.0,
        "ewma_alpha": 0.35,
        "creep_slope_min": 5.0,
    },
    "error_rate": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 2.0,
        "critical_threshold": 10.0,
        "ewma_alpha": 0.25,
        "creep_slope_min": 0.05,
    },
    "db_pool_utilization": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 70.0,
        "critical_threshold": 85.0,
        "ewma_alpha": 0.15,
        "creep_slope_min": 0.05,
    },
    "availability_pct": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 99.0,  # Below 99% is warning
        "critical_threshold": 95.0,  # Below 95% is critical
        "ewma_alpha": 0.2,
        "creep_slope_min": -0.05,  # Negative slope = declining
    },
    "dependency_health": {
        "unit": "%",
        "min_possible": 0.0,
        "max_possible": 100.0,
        "warn_threshold": 80.0,
        "critical_threshold": 50.0,
        "ewma_alpha": 0.25,
        "creep_slope_min": -0.1,
    },
    "request_rate": {
        "unit": "RPS",
        "min_possible": 0.0,
        "max_possible": 5000.0,
        "warn_threshold": 120.0,
        "critical_threshold": 300.0,
        "ewma_alpha": 0.3,
        "creep_slope_min": 0.5,
    },
}

# Multi-Signal Correlation Clusters
# Maps primary anomaly symptoms to correlated secondary signals for root cause context
CORRELATION_CLUSTERS = [
    {
        "name": "Memory Leak & Heap Exhaustion",
        "primary": "memory_utilization",
        "corroborating": ["latency_p95_ms", "cpu_utilization"],
        "explanation": "Progressive memory saturation induced GC pauses and tail latency inflation.",
    },
    {
        "name": "Database Connection Pool Starvation",
        "primary": "db_pool_utilization",
        "corroborating": ["latency_p95_ms", "error_rate"],
        "explanation": "Database pool saturation exhausted available connections, causing caller transaction timeouts.",
    },
    {
        "name": "Downstream Dependency Failure",
        "primary": "error_rate",
        "corroborating": ["dependency_health", "latency_p95_ms"],
        "explanation": "Elevated HTTP error rate coincided with degraded downstream dependency health.",
    },
    {
        "name": "Disk Storage Depletion",
        "primary": "disk_utilization",
        "corroborating": ["availability_pct", "error_rate"],
        "explanation": "Persistent disk growth approached filesystem capacity, threatening process availability.",
    },
    {
        "name": "Traffic Surge Saturation",
        "primary": "request_rate",
        "corroborating": ["cpu_utilization", "latency_p95_ms", "network_throughput_mbps"],
        "explanation": "Inbound request spike exceeded compute capacity, inducing queue buffering and latency drift.",
    },
]


def classify_anomaly_severity(
    metric_name: str,
    observed_value: float,
    baseline_value: float,
    z_score: float,
    is_creep: bool,
    corroborating_count: int,
    confidence: float,
    service_tier: str = "Tier-1",
) -> AnomalySeverity:
    """
    Deterministic rule-based severity classifier.
    Combines deviation magnitude, metric threshold, corroboration, and service criticality.
    """
    cfg = METRIC_CONSTRAINTS.get(metric_name, {})
    crit_thresh = cfg.get("critical_threshold")
    warn_thresh = cfg.get("warn_threshold")

    # Inverted metrics (availability, dependency health) where lower is worse
    inverted = metric_name in ["availability_pct", "dependency_health"]

    # 1. Check for absolute critical threshold breach
    if crit_thresh is not None:
        if inverted and observed_value <= crit_thresh:
            return AnomalySeverity.CRITICAL
        elif not inverted and observed_value >= crit_thresh:
            return AnomalySeverity.CRITICAL

    # 2. Multi-signal correlated severe anomaly
    if corroborating_count >= 2 and (z_score >= 4.0 or is_creep):
        return AnomalySeverity.CRITICAL if service_tier == "Tier-1" else AnomalySeverity.HIGH

    # 3. High severity conditions
    if z_score >= 5.0 or (warn_thresh and not inverted and observed_value >= warn_thresh and corroborating_count >= 1):
        return AnomalySeverity.HIGH
    if is_creep and confidence >= 0.8:
        return AnomalySeverity.HIGH if service_tier == "Tier-1" else AnomalySeverity.MEDIUM

    # 4. Medium severity conditions
    if z_score >= 3.0 or is_creep:
        return AnomalySeverity.MEDIUM
    if warn_thresh is not None:
        if (inverted and observed_value <= warn_thresh) or (not inverted and observed_value >= warn_thresh):
            return AnomalySeverity.MEDIUM

    # 5. Low / Info
    if z_score >= 2.0:
        return AnomalySeverity.LOW

    return AnomalySeverity.INFO
