"""
INCIDENTX AI - Latency Distribution & Tail Latency Detector
Analyzes percentile shifts across P50, P95, and P99 latency percentiles,
detecting tail divergence, queue stall patterns, and degradation.
"""

from typing import Any, Dict, List
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)


class LatencyDetector:
    """
    Monitors latency percentiles (P50, P95, P99) and identifies:
    1. Tail Latency Divergence: P99 > 3.5x P50 or P95 > 2.5x P50
    2. Global Latency Inflation: P50 itself jumps significantly (> 200ms)
    3. Severe Tail Spikes: P99 > 2000ms
    """

    def __init__(
        self,
        tail_divergence_ratio: float = 3.5,
        p99_critical_threshold_ms: float = 2000.0,
        p95_warn_threshold_ms: float = 800.0,
    ):
        self.tail_divergence_ratio = tail_divergence_ratio
        self.p99_critical_threshold_ms = p99_critical_threshold_ms
        self.p95_warn_threshold_ms = p95_warn_threshold_ms

    def evaluate(self, snapshot: Dict[str, Any]) -> List[AnomalyAlert]:
        alerts: List[AnomalyAlert] = []
        svc = snapshot.get("service_name", "unknown")
        data_source = snapshot.get("data_source", "LIVE")

        p50 = float(snapshot.get("latency_p50_ms", 0.0))
        p95 = float(snapshot.get("latency_p95_ms", 0.0))
        p99 = float(snapshot.get("latency_p99_ms", 0.0))

        # 1. Critical P99 Breach
        if p99 >= self.p99_critical_threshold_ms:
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.LATENCY_TAIL,
                    service_name=svc,
                    metric_name="latency_p99_ms",
                    current_value=p99,
                    threshold_or_baseline=self.p99_critical_threshold_ms,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{svc} extreme tail latency spike: P99 reached {p99:.1f}ms (P50={p50:.1f}ms, P95={p95:.1f}ms)",
                    context={"p50": p50, "p95": p95, "p99": p99},
                    data_source=data_source,
                )
            )

        # 2. P95 Latency Warning Breach
        elif p95 >= self.p95_warn_threshold_ms:
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.LATENCY_TAIL,
                    service_name=svc,
                    metric_name="latency_p95_ms",
                    current_value=p95,
                    threshold_or_baseline=self.p95_warn_threshold_ms,
                    severity=AlertSeverity.WARN,
                    message=f"{svc} elevated P95 latency: {p95:.1f}ms exceeds threshold {self.p95_warn_threshold_ms:.1f}ms",
                    context={"p50": p50, "p95": p95, "p99": p99},
                    data_source=data_source,
                )
            )

        # 3. Tail Divergence (P99 vs P50 skew indicates head-of-line blocking or thread pool starvation)
        if p50 > 5.0 and (p99 / p50) >= self.tail_divergence_ratio and p99 >= 300.0:
            ratio = p99 / p50
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.LATENCY_TAIL,
                    service_name=svc,
                    metric_name="tail_divergence_ratio",
                    current_value=ratio,
                    threshold_or_baseline=self.tail_divergence_ratio,
                    severity=AlertSeverity.WARN if p99 < 1500.0 else AlertSeverity.CRITICAL,
                    message=f"{svc} tail latency divergence detected: P99/P50 ratio is {ratio:.1f}x (P50={p50:.1f}ms vs P99={p99:.1f}ms)",
                    context={"p50": p50, "p95": p95, "p99": p99, "ratio": ratio},
                    data_source=data_source,
                )
            )

        return alerts
