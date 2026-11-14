"""
INCIDENTX AI - Explainable Telemetry Anomaly Detection Engine (Phase 8.3)
Implements deterministic, explainable statistical & threshold-based anomaly detection.
Features rolling Z-score baselining, consecutive breach anti-flapping, and alert deduplication.
"""

import math
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.infrastructure.core.infrastructure_models import TelemetryAnomalyRecord


class AnomalyBreachTracker:
    """Tracks consecutive threshold breaches and cooldowns for a resource+metric tuple."""
    def __init__(self, required_consecutive_breaches: int = 3, cooldown_seconds: float = 60.0):
        self.required_consecutive_breaches = required_consecutive_breaches
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_count: int = 0
        self.last_alert_time: Optional[float] = None
        self.history: deque = deque(maxlen=50)

    def record_sample(self, val: float) -> None:
        self.history.append(val)

    def calculate_stats(self) -> Tuple[float, float]:
        if not self.history:
            return 0.0, 0.0
        n = len(self.history)
        mean = sum(self.history) / n
        if n < 2:
            return mean, 0.0
        variance = sum((x - mean) ** 2 for x in self.history) / (n - 1)
        return mean, math.sqrt(variance)


class TelemetryAnomalyEngine:
    """
    Explainable statistical anomaly detector independent of black-box LLMs.
    """

    STATIC_THRESHOLDS: Dict[str, Dict[str, Any]] = {
        "cpu_utilization": {"threshold": 80.0, "unit": "%", "operator": ">", "severity": "HIGH"},
        "container_cpu_cores": {"threshold": 1.5, "unit": "cores", "operator": ">", "severity": "HIGH"},
        "memory_utilization": {"threshold": 85.0, "unit": "%", "operator": ">", "severity": "CRITICAL"},
        "container_memory_bytes": {"threshold": 1073741824, "unit": "bytes", "operator": ">", "severity": "CRITICAL"},
        "error_rate": {"threshold": 5.0, "unit": "%", "operator": ">", "severity": "CRITICAL"},
        "latency_p95_ms": {"threshold": 800.0, "unit": "ms", "operator": ">", "severity": "HIGH"},
        "db_pool_utilization": {"threshold": 80.0, "unit": "%", "operator": ">", "severity": "HIGH"},
        "pod_restart_count": {"threshold": 1.0, "unit": "restarts", "operator": ">", "severity": "HIGH"},
    }

    def __init__(self, consecutive_breaches_required: int = 3, default_sigma_threshold: float = 3.0):
        self.consecutive_breaches_required = consecutive_breaches_required
        self.default_sigma_threshold = default_sigma_threshold
        # Key: (resource_name, metric_name) -> AnomalyBreachTracker
        self._trackers: Dict[Tuple[str, str], AnomalyBreachTracker] = {}
        # Ring buffer of detected anomalies
        self._detected_anomalies: deque = deque(maxlen=200)

    def _get_tracker(self, resource_name: str, metric_name: str) -> AnomalyBreachTracker:
        key = (resource_name, metric_name)
        if key not in self._trackers:
            self._trackers[key] = AnomalyBreachTracker(
                required_consecutive_breaches=self.consecutive_breaches_required
            )
        return self._trackers[key]

    def evaluate_metric(
        self,
        resource_name: str,
        metric_name: str,
        current_value: float,
        data_source: str = "PROMETHEUS",
        timestamp: Optional[str] = None,
    ) -> Optional[TelemetryAnomalyRecord]:
        """
        Evaluate a single metric observation against static thresholds and rolling baselines.
        Returns a TelemetryAnomalyRecord if a confirmed anomaly is detected (satisfying consecutive breach rules).
        """
        now_ts = timestamp or datetime.now(timezone.utc).isoformat()
        tracker = self._get_tracker(resource_name, metric_name)
        tracker.record_sample(current_value)

        mean, std_dev = tracker.calculate_stats()
        is_breaching = False
        detector_type = "STATIC_THRESHOLD"
        threshold_val = 0.0
        deviation_sigma = None
        severity = "WARN"
        explanation = ""

        # 1. Evaluate Static Threshold
        static_rule = self.STATIC_THRESHOLDS.get(metric_name)
        if static_rule:
            th = static_rule["threshold"]
            threshold_val = th
            if static_rule["operator"] == ">" and current_value > th:
                is_breaching = True
                detector_type = "STATIC_THRESHOLD"
                severity = static_rule["severity"]
                explanation = (
                    f"{metric_name} ({current_value:.2f}{static_rule['unit']}) breached static threshold "
                    f"of {th:.2f}{static_rule['unit']} on {resource_name}."
                )

        # 2. Evaluate Rolling Baseline / Z-Score (if at least 5 history points and not already static-breached)
        if not is_breaching and len(tracker.history) >= 5 and std_dev > 0.001:
            z_score = (current_value - mean) / std_dev
            if z_score >= self.default_sigma_threshold:
                is_breaching = True
                detector_type = "ROLLING_BASELINE"
                threshold_val = mean + (self.default_sigma_threshold * std_dev)
                deviation_sigma = round(z_score, 2)
                severity = "CRITICAL" if z_score > 4.5 else "HIGH"
                explanation = (
                    f"{metric_name} ({current_value:.2f}) deviated from rolling baseline mean "
                    f"({mean:.2f}) by {z_score:.1f} standard deviations (threshold: {threshold_val:.2f}) on {resource_name}."
                )

        # 3. Handle Consecutive Breach Logic (Anti-Flapping)
        if is_breaching:
            tracker.consecutive_count += 1
            if tracker.consecutive_count >= self.consecutive_breaches_required:
                # Confirmed anomaly!
                anomaly_rec = TelemetryAnomalyRecord(
                    id=f"anomaly-{uuid.uuid4().hex[:8]}",
                    timestamp=now_ts,
                    metric_name=metric_name,
                    resource_name=resource_name,
                    detector_type=detector_type,
                    current_value=round(current_value, 2),
                    baseline_value=round(mean, 2),
                    threshold_value=round(threshold_val, 2),
                    deviation_sigma=deviation_sigma,
                    consecutive_breaches=tracker.consecutive_count,
                    severity=severity,
                    explanation=f"{explanation} (Confirmed after {tracker.consecutive_count} consecutive sample breaches).",
                    data_source=data_source,
                )
                self._detected_anomalies.append(anomaly_rec)
                return anomaly_rec
        else:
            # Reset consecutive count on normal sample
            tracker.consecutive_count = 0

        return None

    def list_recent_anomalies(self, limit: int = 50) -> List[TelemetryAnomalyRecord]:
        return list(reversed(self._detected_anomalies))[:limit]

    def clear(self) -> None:
        self._trackers.clear()
        self._detected_anomalies.clear()


# Global singleton instance
telemetry_anomaly_engine = TelemetryAnomalyEngine()
