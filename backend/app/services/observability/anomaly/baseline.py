"""
INCIDENTX AI - Dynamic Adaptive Baseline Engine
Computes rolling statistical baselines (mean, variance, normal operating bands)
while preventing abnormal measurements from contaminating historical baselines.
"""

from collections import deque
import math
from typing import Any, Deque, Dict, List, Optional, Tuple

from backend.app.services.observability.anomaly.rules import METRIC_CONSTRAINTS


class MetricBaseline:
    """Represents a computed statistical baseline for a specific (service, metric)."""

    def __init__(
        self,
        service_name: str,
        metric_name: str,
        mean: float,
        std_dev: float,
        min_normal: float,
        max_normal: float,
        sample_count: int,
        has_sufficient_history: bool,
    ):
        self.service_name = service_name
        self.metric_name = metric_name
        self.mean = round(mean, 2)
        self.std_dev = round(std_dev, 2)
        self.min_normal = round(min_normal, 2)
        self.max_normal = round(max_normal, 2)
        self.sample_count = sample_count
        self.has_sufficient_history = has_sufficient_history

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "min_normal": self.min_normal,
            "max_normal": self.max_normal,
            "sample_count": self.sample_count,
            "has_sufficient_history": self.has_sufficient_history,
        }


class DynamicBaselineEngine:
    """
    Maintains clean, uncontaminated rolling metric baselines per microservice.
    Enforces minimum sample thresholds and outlier rejection to prevent baseline poisoning.
    """

    def __init__(
        self,
        window_size: int = 60,
        min_samples: int = 10,
        z_threshold: float = 3.0,
    ):
        self.window_size = window_size
        self.min_samples = min_samples
        self.z_threshold = z_threshold

        # Historical clean sample buffer: key = (service_name, metric_name)
        self._buffers: Dict[Tuple[str, str], Deque[float]] = {}

    def add_observation(
        self,
        service_name: str,
        metric_name: str,
        value: Any,
        is_known_anomaly: bool = False,
    ) -> bool:
        """
        Records a metric observation if valid and not contaminating the clean baseline.
        Returns True if accepted into the baseline, False if rejected or quarantined.
        """
        if value is None:
            return False

        try:
            val_f = float(value)
            if math.isnan(val_f) or math.isinf(val_f):
                return False
        except (ValueError, TypeError):
            return False

        key = (service_name, metric_name)
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self.window_size)

        buf = self._buffers[key]

        # Contamination Prevention:
        # If explicitly flagged as active anomaly or severely deviates from established baseline, reject
        if is_known_anomaly:
            return False

        if len(buf) >= self.min_samples:
            mean, std_dev = self._compute_mean_std(list(buf))
            # Prevent contamination: if severe outlier from mean
            effective_std = max(0.5, std_dev)
            z_score = abs(val_f - mean) / effective_std
            if z_score >= 3.5 or abs(val_f - mean) >= 10.0:
                return False  # Prevent contamination

        buf.append(val_f)
        return True

    def get_baseline(self, service_name: str, metric_name: str) -> MetricBaseline:
        """Computes point-in-time baseline statistics for a service metric."""
        key = (service_name, metric_name)
        buf = self._buffers.get(key)
        cfg = METRIC_CONSTRAINTS.get(metric_name, {})

        if not buf or len(buf) < self.min_samples:
            # Insufficient history: fallback to static configuration limits
            min_possible = cfg.get("min_possible", 0.0)
            max_possible = cfg.get("max_possible", 100.0)
            warn_val = cfg.get("warn_threshold", 80.0)
            fallback_mean = (warn_val + min_possible) / 2.0
            return MetricBaseline(
                service_name=service_name,
                metric_name=metric_name,
                mean=fallback_mean,
                std_dev=0.0,
                min_normal=min_possible,
                max_normal=warn_val,
                sample_count=len(buf) if buf else 0,
                has_sufficient_history=False,
            )

        samples = list(buf)
        mean, std_dev = self._compute_mean_std(samples)

        # Baseline operating band: mean +- (z_threshold * std_dev)
        min_possible = cfg.get("min_possible", 0.0)
        max_possible = cfg.get("max_possible", 100.0)

        min_normal = max(min_possible, mean - (self.z_threshold * std_dev))
        max_normal = min(max_possible, mean + (self.z_threshold * std_dev))

        return MetricBaseline(
            service_name=service_name,
            metric_name=metric_name,
            mean=mean,
            std_dev=std_dev,
            min_normal=min_normal,
            max_normal=max_normal,
            sample_count=len(samples),
            has_sufficient_history=True,
        )

    def get_all_service_baselines(self, service_name: str) -> Dict[str, Dict[str, Any]]:
        """Returns baseline statistics for all 10 Golden Signals for a service."""
        result = {}
        for m_name in METRIC_CONSTRAINTS.keys():
            result[m_name] = self.get_baseline(service_name, m_name).to_dict()
        return result

    @staticmethod
    def _compute_mean_std(samples: List[float]) -> Tuple[float, float]:
        """Calculates arithmetic mean and sample standard deviation."""
        n = len(samples)
        if n == 0:
            return 0.0, 0.0
        mean = sum(samples) / n
        if n < 2:
            return mean, 0.0
        variance = sum((x - mean) ** 2 for x in samples) / (n - 1)
        return mean, math.sqrt(max(0.0, variance))
