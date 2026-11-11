"""
INCIDENTX AI - Predictive Reliability Package (Stage 5.5)
Detects infrastructure degradation before incidents happen using trend models,
EWMA slopes, Time-to-Exhaustion (TTE), predictive warnings, and capacity risk scoring.
"""

from backend.app.services.predictive.models import (
    CapacityRiskSummary,
    ForecastPoint,
    ResourcePrediction,
)
from backend.app.services.predictive.trend_models import (
    DEFAULT_EXHAUSTION_THRESHOLDS,
    calculate_ewma_trend,
    calculate_ols_trend,
    calculate_tte,
    get_metric_threshold,
)
from backend.app.services.predictive.engine import (
    PredictiveReliabilityEngine,
    TRACKED_PREDICTIVE_METRICS,
)

__all__ = [
    "CapacityRiskSummary",
    "ForecastPoint",
    "ResourcePrediction",
    "DEFAULT_EXHAUSTION_THRESHOLDS",
    "calculate_ewma_trend",
    "calculate_ols_trend",
    "calculate_tte",
    "get_metric_threshold",
    "PredictiveReliabilityEngine",
    "TRACKED_PREDICTIVE_METRICS",
]
