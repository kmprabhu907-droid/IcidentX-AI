"""
INCIDENTX AI - Resource-Creep & Degradation Trend Analyzer
Uses Ordinary Least Squares (OLS) linear regression over sliding historical windows
to identify gradual memory leaks, connection pool exhaustion, and storage growth.
Calculates trend slope, R-squared goodness-of-fit, and Time-to-Exhaustion (TTE).
"""

from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Deque, Dict, List, Optional, Tuple

from backend.app.services.observability.anomaly.rules import METRIC_CONSTRAINTS


class TrendObservation:
    def __init__(self, timestamp: float, value: float):
        self.timestamp = timestamp
        self.value = value


class ResourceCreepDetector:
    """
    Detects gradual, sustained degradation across resources:
    - Gradual memory growth (memory leaks)
    - Database connection-pool leakage
    - Disk utilization growth
    - CPU usage creep
    - Progressive request latency inflation
    - Error rate upward drift
    """

    def __init__(
        self,
        window_size: int = 45,
        min_samples: int = 10,
        min_r_squared: float = 0.65,
    ):
        self.window_size = window_size
        self.min_samples = min_samples
        self.min_r_squared = min_r_squared

        # Key: (service_name, metric_name) -> Deque[TrendObservation]
        self._windows: Dict[Tuple[str, str], Deque[TrendObservation]] = {}

    def add_sample(self, service_name: str, metric_name: str, value: Any, timestamp: Optional[datetime] = None):
        """Records a timestamped sample in the sliding trend analysis window."""
        if value is None:
            return

        try:
            val_f = float(value)
            if math.isnan(val_f) or math.isinf(val_f):
                return
        except (ValueError, TypeError):
            return

        t = timestamp.timestamp() if timestamp else datetime.now(timezone.utc).timestamp()
        key = (service_name, metric_name)
        if key not in self._windows:
            self._windows[key] = deque(maxlen=self.window_size)

        self._windows[key].append(TrendObservation(t, val_f))

    def evaluate_creep(
        self,
        service_name: str,
        metric_name: str,
        current_value: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes linear regression on historical observations.
        Returns a creep analysis dictionary if sustained upward trend is verified, else None.
        """
        key = (service_name, metric_name)
        buf = self._windows.get(key)
        if not buf or len(buf) < self.min_samples:
            return None

        cfg = METRIC_CONSTRAINTS.get(metric_name, {})
        min_slope = cfg.get("creep_slope_min", 0.05)
        crit_thresh = cfg.get("critical_threshold")

        samples = list(buf)
        n = len(samples)

        # Normalize timestamps relative to first sample (t0 = 0.0s)
        t0 = samples[0].timestamp
        t_values = [s.timestamp - t0 for s in samples]
        x_values = [s.value for s in samples]

        # Ensure time has elapsed
        time_span = t_values[-1] - t_values[0]
        if time_span < 5.0:
            return None

        # OLS Linear Regression: y = m * t + c
        t_mean = sum(t_values) / n
        x_mean = sum(x_values) / n

        numerator = sum((t_values[i] - t_mean) * (x_values[i] - x_mean) for i in range(n))
        denominator = sum((t_values[i] - t_mean) ** 2 for i in range(n))

        if denominator == 0.0:
            return None

        slope = numerator / denominator
        intercept = x_mean - (slope * t_mean)

        # Goodness-of-fit: R-squared
        ss_tot = sum((x - x_mean) ** 2 for x in x_values)
        if ss_tot == 0.0:
            # Flat line
            return None

        ss_res = sum((x_values[i] - (slope * t_values[i] + intercept)) ** 2 for i in range(n))
        r_squared = max(0.0, 1.0 - (ss_res / ss_tot))

        # Check for directional creep matching threshold
        inverted = metric_name in ["availability_pct", "dependency_health"]
        is_creeping = False

        if not inverted:
            # Upward creep
            if slope >= min_slope and r_squared >= self.min_r_squared:
                is_creeping = True
        else:
            # Downward degradation
            if slope <= min_slope and r_squared >= self.min_r_squared:
                is_creeping = True

        if not is_creeping:
            return None

        # Rate of change per minute
        rate_per_minute = slope * 60.0

        # Estimated Threshold-Crossing Time (TTE) in seconds
        tte_seconds: Optional[float] = None
        if crit_thresh is not None:
            if not inverted and slope > 0 and current_value < crit_thresh:
                tte_seconds = round((crit_thresh - current_value) / slope, 1)
            elif inverted and slope < 0 and current_value > crit_thresh:
                tte_seconds = round((crit_thresh - current_value) / slope, 1)

        return {
            "is_creep": True,
            "slope": round(slope, 4),
            "rate_per_minute": round(rate_per_minute, 2),
            "r_squared": round(r_squared, 3),
            "time_window_seconds": round(time_span, 1),
            "sample_count": n,
            "projected_tte_seconds": tte_seconds,
            "trend_direction": "UPWARD" if slope > 0 else "DOWNWARD",
        }
