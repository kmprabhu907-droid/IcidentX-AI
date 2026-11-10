"""
INCIDENTX AI - Baseline Statistical Anomaly Detector
Computes rolling mean and standard deviation over historical windows,
detecting statistical anomalies (3-sigma / z-score >= 3.0) with minimum sample requirements.
"""

import math
from typing import Any, Dict, List, Optional
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)


class BaselineDetector:
    """
    Evaluates metric deviations against rolling baseline windows.
    Detects sudden distribution drift exceeding z-score thresholds (3-sigma rule).
    Enforces minimum observation count (default N >= 10).
    """

    METRICS_TO_TRACK = [
        "latency_p95_ms",
        "error_rate",
        "cpu_utilization",
        "request_rate",
    ]

    def __init__(
        self,
        min_samples: int = 10,
        z_score_threshold: float = 3.0,
        window_size: int = 60,
    ):
        self.min_samples = min_samples
        self.z_score_threshold = z_score_threshold
        self.window_size = window_size

    def evaluate(
        self,
        current_snapshot: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> List[AnomalyAlert]:
        """
        Evaluate current metrics against historical baseline.
        history: list of prior snapshots chronologically ordered.
        """
        alerts: List[AnomalyAlert] = []
        svc = current_snapshot.get("service_name", "unknown")
        data_source = current_snapshot.get("data_source", "LIVE")

        if len(history) < self.min_samples:
            # Not enough historical baseline observations yet
            return alerts

        # Use up to window_size history entries
        baseline_slice = history[-self.window_size :]

        for metric in self.METRICS_TO_TRACK:
            if metric not in current_snapshot or current_snapshot[metric] is None:
                continue

            current_val = float(current_snapshot[metric])
            vals = [float(item[metric]) for item in baseline_slice if metric in item and item[metric] is not None]

            if len(vals) < self.min_samples:
                continue

            mean = sum(vals) / len(vals)
            variance = sum((x - mean) ** 2 for x in vals) / len(vals)
            std_dev = math.sqrt(variance)

            # Avoid division by zero on flat baselines
            effective_std_dev = max(std_dev, 0.05 * (mean if mean > 0 else 1.0))
            z_score = (current_val - mean) / effective_std_dev

            # Check if z-score exceeds threshold in positive deviation (or absolute for error rate/latency)
            if z_score >= self.z_score_threshold:
                severity = AlertSeverity.CRITICAL if z_score >= 4.5 else AlertSeverity.WARN
                alerts.append(
                    AnomalyAlert(
                        detector_type=DetectorType.BASELINE_DEVIATION,
                        service_name=svc,
                        metric_name=metric,
                        current_value=current_val,
                        threshold_or_baseline=mean,
                        deviation_sigma=z_score,
                        severity=severity,
                        message=(
                            f"{svc} {metric} statistical anomaly: value {current_val:.1f} deviates "
                            f"{z_score:.1f}σ from baseline mean {mean:.1f} (std={std_dev:.2f}, N={len(vals)})"
                        ),
                        context={
                            "baseline_mean": round(mean, 2),
                            "baseline_std": round(std_dev, 2),
                            "sample_count": len(vals),
                            "z_score": round(z_score, 2),
                        },
                        data_source=data_source,
                    )
                )

        return alerts
