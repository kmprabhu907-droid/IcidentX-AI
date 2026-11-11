"""
INCIDENTX AI - Exponentially Weighted Moving Average (EWMA) Engine
Implements EWMA smoothing: EWMA(t) = alpha * X(t) + (1 - alpha) * EWMA(t-1)
Detects both sudden transient spikes and sustained systemic metric shifts.
"""

from collections import deque
import math
from typing import Any, Deque, Dict, Optional, Tuple

from backend.app.services.observability.anomaly.rules import METRIC_CONSTRAINTS


class EWMATracker:
    """Tracks EWMA state and historical smoothed trajectory for a single metric."""

    def __init__(self, service_name: str, metric_name: str, alpha: float = 0.2):
        self.service_name = service_name
        self.metric_name = metric_name
        self.alpha = min(1.0, max(0.01, alpha))
        self.current_ewma: Optional[float] = None
        self.history: Deque[float] = deque(maxlen=60)
        self.observation_count: int = 0

    def update(self, value: Any) -> Optional[float]:
        """
        Ingests a new metric value, updates EWMA, and returns the smoothed value.
        Safely ignores None, NaN, and Inf.
        """
        if value is None:
            return self.current_ewma

        try:
            val_f = float(value)
            if math.isnan(val_f) or math.isinf(val_f):
                return self.current_ewma
        except (ValueError, TypeError):
            return self.current_ewma

        if self.current_ewma is None:
            # Cold start: initialize EWMA with first observed value
            self.current_ewma = val_f
        else:
            self.current_ewma = (self.alpha * val_f) + ((1.0 - self.alpha) * self.current_ewma)

        self.current_ewma = round(self.current_ewma, 2)
        self.history.append(self.current_ewma)
        self.observation_count += 1
        return self.current_ewma


class EWMAEngine:
    """
    Manages EWMA trackers across all services and metrics.
    Detects sudden spikes and sustained regime shifts.
    """

    def __init__(self):
        # Key: (service_name, metric_name) -> EWMATracker
        self._trackers: Dict[Tuple[str, str], EWMATracker] = {}

    def get_or_create_tracker(self, service_name: str, metric_name: str) -> EWMATracker:
        """Retrieves or instantiates an EWMA tracker with metric-specific alpha."""
        key = (service_name, metric_name)
        if key not in self._trackers:
            alpha = METRIC_CONSTRAINTS.get(metric_name, {}).get("ewma_alpha", 0.2)
            self._trackers[key] = EWMATracker(
                service_name=service_name,
                metric_name=metric_name,
                alpha=alpha,
            )
        return self._trackers[key]

    def update(self, service_name: str, metric_name: str, value: Any) -> Optional[float]:
        """Updates EWMA for a service metric and returns the current smoothed value."""
        tracker = self.get_or_create_tracker(service_name, metric_name)
        return tracker.update(value)

    def evaluate_deviation(
        self,
        service_name: str,
        metric_name: str,
        observed_value: float,
        baseline_mean: float,
        baseline_std: float,
    ) -> Dict[str, Any]:
        """
        Evaluates whether current observed and EWMA smoothed values indicate
        a sudden deviation or a sustained deviation from normal baseline.
        """
        tracker = self.get_or_create_tracker(service_name, metric_name)
        current_ewma = tracker.current_ewma if tracker.current_ewma is not None else observed_value

        std_dev = max(0.01, baseline_std)
        raw_deviation = abs(observed_value - baseline_mean)
        ewma_deviation = abs(current_ewma - baseline_mean)

        raw_z = raw_deviation / std_dev
        ewma_z = ewma_deviation / std_dev

        # Sudden spike: raw z-score is high while EWMA is just beginning to react
        is_sudden_spike = raw_z >= 3.0 and abs(observed_value - current_ewma) >= (2.0 * std_dev)

        # Sustained shift: smoothed EWMA itself has moved significantly past baseline
        is_sustained_shift = ewma_z >= 2.5 and tracker.observation_count >= 5

        return {
            "current_ewma": current_ewma,
            "raw_z_score": round(raw_z, 2),
            "ewma_z_score": round(ewma_z, 2),
            "is_sudden_spike": is_sudden_spike,
            "is_sustained_shift": is_sustained_shift,
            "observation_count": tracker.observation_count,
        }
