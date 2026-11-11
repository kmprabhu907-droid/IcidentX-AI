"""
INCIDENTX AI - Predictive Trend & Exhaustion Math Models
Provides Ordinary Least Squares (OLS) regression, EWMA trend momentum,
Time-to-Exhaustion (TTE = (Threshold - Current) / Growth Rate), and statistical bounds.
"""

import math
from typing import Dict, List, Optional, Tuple

# SRE standard operational exhaustion thresholds
DEFAULT_EXHAUSTION_THRESHOLDS: Dict[str, float] = {
    "db_pool_utilization": 95.0,     # Percentage (0 - 100)
    "memory_utilization": 90.0,      # Percentage (0 - 100)
    "disk_utilization": 90.0,        # Percentage (0 - 100)
    "cpu_utilization": 90.0,         # Percentage (0 - 100)
    "error_rate": 0.05,              # 5% error rate (0.0 - 1.0)
    "latency_p95_ms": 1000.0,        # Milliseconds
    "latency_p99_ms": 2500.0,        # Milliseconds
    "network_throughput_mbps": 100.0 # MB/s network saturation
}


def get_metric_threshold(metric_name: str) -> float:
    """Returns established exhaustion threshold for a metric, or default 90.0."""
    return DEFAULT_EXHAUSTION_THRESHOLDS.get(metric_name, 90.0)


def calculate_ols_trend(
    time_series: List[Tuple[float, float]],
) -> Tuple[float, float, float, float]:
    """
    Computes Ordinary Least Squares (OLS) linear trend for a sequence of (t_sec, value) pairs.
    Returns:
      (slope, intercept, r_squared, std_err)
      where slope is value change per second.
    """
    n = len(time_series)
    if n < 2:
        return 0.0, time_series[0][1] if n == 1 else 0.0, 0.0, 0.0

    sum_x = sum(pt[0] for pt in time_series)
    sum_y = sum(pt[1] for pt in time_series)
    mean_x = sum_x / n
    mean_y = sum_y / n

    denom = sum((pt[0] - mean_x) ** 2 for pt in time_series)
    if abs(denom) < 1e-9:
        return 0.0, mean_y, 0.0, 0.0

    numer = sum((pt[0] - mean_x) * (pt[1] - mean_y) for pt in time_series)
    slope = numer / denom
    intercept = mean_y - slope * mean_x

    # Compute Total Sum of Squares (TSS) and Residual Sum of Squares (RSS)
    tss = sum((pt[1] - mean_y) ** 2 for pt in time_series)
    rss = sum((pt[1] - (slope * pt[0] + intercept)) ** 2 for pt in time_series)

    if tss < 1e-9:
        r_squared = 1.0 if rss < 1e-9 else 0.0
    else:
        r_squared = max(0.0, min(1.0, 1.0 - (rss / tss)))

    # Standard error of regression estimate
    std_err = math.sqrt(rss / (n - 2)) if n > 2 else 0.0

    return slope, intercept, r_squared, std_err


def calculate_ewma_trend(
    time_series: List[Tuple[float, float]],
    alpha: float = 0.2,
) -> float:
    """
    Calculates Exponentially Weighted Moving Average (EWMA) trend slope per second.
    Discounts momentary burst noise and weights sustained recent growth momentum.
    """
    n = len(time_series)
    if n < 2:
        return 0.0

    # Calculate step delta slopes
    slopes: List[float] = []
    for i in range(1, n):
        dt = time_series[i][0] - time_series[i - 1][0]
        if dt > 0.01:
            dy = time_series[i][1] - time_series[i - 1][1]
            slopes.append(dy / dt)

    if not slopes:
        return 0.0

    # Apply EWMA filter
    ewma_slope = slopes[0]
    for s in slopes[1:]:
        ewma_slope = alpha * s + (1.0 - alpha) * ewma_slope

    return ewma_slope


def calculate_tte(
    current_value: float,
    threshold: float,
    growth_rate_per_sec: float,
) -> Optional[float]:
    """
    Calculates Time-to-Exhaustion (TTE = (Threshold - Current) / Growth Rate) in seconds.
    Returns:
      - 0.0 if current_value >= threshold (already exhausted)
      - None if growth_rate_per_sec <= 1e-6 (stable or recovering)
      - float seconds to threshold breach if positive growth rate
    """
    if current_value >= threshold:
        return 0.0

    if growth_rate_per_sec <= 1e-6:
        return None

    tte = (threshold - current_value) / growth_rate_per_sec
    return max(0.0, tte)
