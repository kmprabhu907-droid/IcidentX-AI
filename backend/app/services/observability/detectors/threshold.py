"""
INCIDENTX AI - Static Threshold Detector
Evaluates metric snapshots against configurable absolute operational thresholds.
"""

from typing import Any, Dict, List
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)


class StaticThresholdDetector:
    """
    Evaluates static boundary thresholds for:
    - CPU utilization
    - Memory utilization
    - Error rate
    - Request latency (P95)
    - Database connection pool utilization
    """

    DEFAULT_THRESHOLDS = {
        "cpu_utilization": {"warn": 80.0, "critical": 90.0, "unit": "%"},
        "memory_utilization": {"warn": 85.0, "critical": 92.0, "unit": "%"},
        "error_rate": {"warn": 5.0, "critical": 15.0, "unit": "%"},
        "latency_p95_ms": {"warn": 500.0, "critical": 1500.0, "unit": "ms"},
        "db_pool_utilization": {"warn": 75.0, "critical": 90.0, "unit": "%"},
    }

    def __init__(self, thresholds: Dict[str, Dict[str, float]] = None):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def evaluate(self, snapshot: Dict[str, Any]) -> List[AnomalyAlert]:
        """
        Evaluate a single service metric snapshot against static threshold limits.
        """
        alerts: List[AnomalyAlert] = []
        svc = snapshot.get("service_name", "unknown")
        data_source = snapshot.get("data_source", "LIVE")

        for metric, rule in self.thresholds.items():
            if metric not in snapshot or snapshot[metric] is None:
                continue

            val = float(snapshot[metric])
            crit_val = rule["critical"]
            warn_val = rule["warn"]
            unit = rule.get("unit", "")

            if val >= crit_val:
                alerts.append(
                    AnomalyAlert(
                        detector_type=DetectorType.STATIC_THRESHOLD,
                        service_name=svc,
                        metric_name=metric,
                        current_value=val,
                        threshold_or_baseline=crit_val,
                        severity=AlertSeverity.CRITICAL,
                        message=f"{svc} {metric} critical breach: {val:.1f}{unit} exceeds threshold {crit_val:.1f}{unit}",
                        context={"threshold_type": "critical", "unit": unit},
                        data_source=data_source,
                    )
                )
            elif val >= warn_val:
                alerts.append(
                    AnomalyAlert(
                        detector_type=DetectorType.STATIC_THRESHOLD,
                        service_name=svc,
                        metric_name=metric,
                        current_value=val,
                        threshold_or_baseline=warn_val,
                        severity=AlertSeverity.WARN,
                        message=f"{svc} {metric} warning breach: {val:.1f}{unit} exceeds threshold {warn_val:.1f}{unit}",
                        context={"threshold_type": "warn", "unit": unit},
                        data_source=data_source,
                    )
                )

        return alerts
