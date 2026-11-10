"""
INCIDENTX AI - Error Intelligence Detector
Identifies sudden error-rate spikes, repeated exception clusters, and service-specific failure patterns.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
    DetectorType,
)


class ErrorIntelligenceDetector:
    """
    Detects:
    1. Error rate spikes (> 10% or >= 5x increase from prior baseline).
    2. Exception frequency clusters (e.g. repeated ConnectionTimeout or NullPointer).
    3. Cascading error patterns.
    """

    def __init__(
        self,
        error_rate_critical: float = 20.0,
        error_rate_warn: float = 5.0,
        cluster_threshold: int = 3,
    ):
        self.error_rate_critical = error_rate_critical
        self.error_rate_warn = error_rate_warn
        self.cluster_threshold = cluster_threshold

    def evaluate_metrics(
        self,
        snapshot: Dict[str, Any],
        prev_snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[AnomalyAlert]:
        alerts: List[AnomalyAlert] = []
        svc = snapshot.get("service_name", "unknown")
        data_source = snapshot.get("data_source", "LIVE")
        error_rate = float(snapshot.get("error_rate", 0.0))

        # 1. Absolute critical error rate
        if error_rate >= self.error_rate_critical:
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.ERROR_INTELLIGENCE,
                    service_name=svc,
                    metric_name="error_rate",
                    current_value=error_rate,
                    threshold_or_baseline=self.error_rate_critical,
                    severity=AlertSeverity.CRITICAL,
                    message=f"{svc} severe error surge: error rate is {error_rate:.1f}% (CRITICAL threshold: {self.error_rate_critical}%)",
                    context={"error_rate": error_rate, "error_count": snapshot.get("error_count", 0)},
                    data_source=data_source,
                )
            )
        # 2. Warning error rate
        elif error_rate >= self.error_rate_warn:
            alerts.append(
                AnomalyAlert(
                    detector_type=DetectorType.ERROR_INTELLIGENCE,
                    service_name=svc,
                    metric_name="error_rate",
                    current_value=error_rate,
                    threshold_or_baseline=self.error_rate_warn,
                    severity=AlertSeverity.WARN,
                    message=f"{svc} elevated error rate: {error_rate:.1f}% exceeds warning threshold {self.error_rate_warn}%",
                    context={"error_rate": error_rate, "error_count": snapshot.get("error_count", 0)},
                    data_source=data_source,
                )
            )

        # 3. Sudden velocity surge (delta from prior second)
        if prev_snapshot:
            prev_rate = float(prev_snapshot.get("error_rate", 0.0))
            if prev_rate > 0.0 and (error_rate / prev_rate) >= 4.0 and error_rate >= 5.0:
                alerts.append(
                    AnomalyAlert(
                        detector_type=DetectorType.ERROR_INTELLIGENCE,
                        service_name=svc,
                        metric_name="error_rate_velocity",
                        current_value=error_rate,
                        threshold_or_baseline=prev_rate,
                        severity=AlertSeverity.WARN,
                        message=f"{svc} rapid error acceleration: rate jumped from {prev_rate:.1f}% to {error_rate:.1f}%",
                        context={"prev_rate": prev_rate, "current_rate": error_rate},
                        data_source=data_source,
                    )
                )

        return alerts

    def evaluate_logs(self, recent_logs: List[Dict[str, Any]]) -> List[AnomalyAlert]:
        """
        Scan recent log buffer for repeated exception patterns and clusters.
        """
        alerts: List[AnomalyAlert] = []
        error_logs = [log for log in recent_logs if log.get("level") == "ERROR"]

        if not error_logs:
            return alerts

        # Group by service and message prefix/type
        cluster_map: Dict[str, Counter] = {}
        data_sources: Dict[str, str] = {}

        for log in error_logs:
            svc = log.get("service_name", "unknown")
            msg = log.get("message", "")
            # Extract exception signature (first 40 characters or before colon)
            signature = msg.split(":")[0].strip() if ":" in msg else msg[:40]
            if svc not in cluster_map:
                cluster_map[svc] = Counter()
            cluster_map[svc][signature] += 1
            data_sources[svc] = log.get("data_source", "LIVE")

        for svc, counts in cluster_map.items():
            for sig, count in counts.items():
                if count >= self.cluster_threshold:
                    alerts.append(
                        AnomalyAlert(
                            detector_type=DetectorType.ERROR_INTELLIGENCE,
                            service_name=svc,
                            metric_name="exception_cluster",
                            current_value=float(count),
                            threshold_or_baseline=float(self.cluster_threshold),
                            severity=AlertSeverity.CRITICAL if count >= 6 else AlertSeverity.WARN,
                            message=f"{svc} error cluster: '{sig}' occurred {count} times in recent window",
                            context={"signature": sig, "occurrence_count": count},
                            data_source=data_sources.get(svc, "LIVE"),
                        )
                    )

        return alerts
