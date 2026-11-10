"""
INCIDENTX AI - Anomaly Detection Data Models
Defines discrete alerts, severities, and detector types emitted by intelligent detection modules.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class DetectorType(str, Enum):
    STATIC_THRESHOLD = "STATIC_THRESHOLD"
    BASELINE_DEVIATION = "BASELINE_DEVIATION"
    LATENCY_TAIL = "LATENCY_TAIL"
    ERROR_INTELLIGENCE = "ERROR_INTELLIGENCE"
    TRAFFIC_INTELLIGENCE = "TRAFFIC_INTELLIGENCE"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class AnomalyAlert:
    """Represents an anomaly alert emitted by one of the 5 detector engines."""
    def __init__(
        self,
        detector_type: DetectorType,
        service_name: str,
        metric_name: str,
        current_value: float,
        threshold_or_baseline: float,
        severity: AlertSeverity,
        message: str,
        deviation_sigma: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        data_source: str = "LIVE",
        timestamp: Optional[datetime] = None,
    ):
        self.alert_id = str(uuid.uuid4())
        self.detector_type = detector_type
        self.service_name = service_name
        self.metric_name = metric_name
        self.current_value = round(current_value, 2)
        self.threshold_or_baseline = round(threshold_or_baseline, 2)
        self.severity = severity
        self.message = message
        self.deviation_sigma = round(deviation_sigma, 2) if deviation_sigma is not None else None
        self.context = context or {}
        self.data_source = data_source
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "detector_type": self.detector_type.value,
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_or_baseline": self.threshold_or_baseline,
            "severity": self.severity.value,
            "message": self.message,
            "deviation_sigma": self.deviation_sigma,
            "context": self.context,
            "data_source": self.data_source,
            "timestamp": self.timestamp.isoformat(),
        }
