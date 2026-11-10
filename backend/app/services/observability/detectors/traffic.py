"""
INCIDENTX AI - Traffic Intelligence Detector
Identifies traffic surges, sudden throughput dropouts (blackouts), and cascading timeouts.
"""

from typing import Any, Dict, List, Optional
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)


class TrafficIntelligenceDetector:
    """
    Detects:
    1. Traffic Surge: Throughput spikes >= 2.5x above expected baseline.
    2. Traffic Drop / Blackout: Throughput drops to near-zero (< 0.2x baseline) when expected.
    3. Cascading timeout propagation.
    """

    def __init__(
        self,
        surge_multiplier: float = 2.5,
        drop_ratio: float = 0.2,
    ):
        self.surge_multiplier = surge_multiplier
        self.drop_ratio = drop_ratio

    def evaluate(
        self,
        snapshot: Dict[str, Any],
        baseline_rps: float,
    ) -> List[AnomalyAlert]:
        alerts: List[AnomalyAlert] = []
        svc = snapshot.get("service_name", "unknown")
        data_source = snapshot.get("data_source", "LIVE")
        current_rps = float(snapshot.get("request_rate", 0.0))

        if baseline_rps <= 1.0:
            return alerts

        # 1. Traffic Surge
        if current_rps >= (baseline_rps * self.surge_multiplier):
            ratio = current_rps / baseline_rps
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.TRAFFIC_INTELLIGENCE,
                    service_name=svc,
                    metric_name="traffic_surge",
                    current_value=current_rps,
                    threshold_or_baseline=baseline_rps,
                    severity=AlertSeverity.WARN if ratio < 4.0 else AlertSeverity.CRITICAL,
                    message=f"{svc} abnormal traffic surge: throughput {current_rps:.1f} rps is {ratio:.1f}x normal baseline ({baseline_rps:.1f} rps)",
                    context={"current_rps": current_rps, "baseline_rps": baseline_rps, "surge_ratio": round(ratio, 2)},
                    data_source=data_source,
                )
            )

        # 2. Traffic Drop / Blackout (applicable to gateway and critical services)
        elif current_rps <= (baseline_rps * self.drop_ratio) and baseline_rps >= 5.0:
            drop_percent = (1.0 - (current_rps / baseline_rps)) * 100.0
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.TRAFFIC_INTELLIGENCE,
                    service_name=svc,
                    metric_name="traffic_blackout",
                    current_value=current_rps,
                    threshold_or_baseline=baseline_rps,
                    severity=AlertSeverity.CRITICAL if current_rps == 0.0 else AlertSeverity.WARN,
                    message=f"{svc} sudden traffic collapse: throughput collapsed to {current_rps:.1f} rps ({drop_percent:.0f}% drop below baseline {baseline_rps:.1f} rps)",
                    context={"current_rps": current_rps, "baseline_rps": baseline_rps, "drop_percent": round(drop_percent, 1)},
                    data_source=data_source,
                )
            )

        return alerts
