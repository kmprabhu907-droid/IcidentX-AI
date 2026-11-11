"""
INCIDENTX AI - Predictive Reliability Models (Stage 5.5)
Defines data structures for time-series forecasting, resource exhaustion,
trend models, and capacity risk scoring.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """Point in time forward projection with confidence interval bounds."""
    timestamp: str = Field(..., description="Projected ISO timestamp")
    minutes_ahead: float = Field(..., description="Minutes from forecast origin")
    predicted_value: float = Field(..., description="Central linear/EWMA projected value")
    lower_bound: float = Field(..., description="Lower bound of 95% confidence interval")
    upper_bound: float = Field(..., description="Upper bound of 95% confidence interval")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "minutes_ahead": round(self.minutes_ahead, 1),
            "predicted_value": round(self.predicted_value, 2),
            "lower_bound": round(self.lower_bound, 2),
            "upper_bound": round(self.upper_bound, 2),
        }


class ResourcePrediction(BaseModel):
    """Proactive metric trend evaluation and exhaustion projection."""
    service_name: str
    metric_name: str
    current_value: float
    growth_rate_per_sec: float
    growth_rate_per_min: float
    exhaustion_threshold: float
    time_to_exhaustion_seconds: Optional[float]
    time_to_exhaustion_minutes: Optional[float]
    r_squared: float
    warning_level: str  # NOMINAL, ADVISORY, WARNING, CRITICAL
    trend_model: str    # LINEAR_OLS, EWMA_MOMENTUM
    sample_count: int
    forecast_points: List[ForecastPoint] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "current_value": round(self.current_value, 2),
            "growth_rate_per_sec": round(self.growth_rate_per_sec, 4),
            "growth_rate_per_min": round(self.growth_rate_per_min, 3),
            "exhaustion_threshold": round(self.exhaustion_threshold, 2),
            "time_to_exhaustion_seconds": round(self.time_to_exhaustion_seconds, 1) if self.time_to_exhaustion_seconds is not None else None,
            "time_to_exhaustion_minutes": round(self.time_to_exhaustion_minutes, 1) if self.time_to_exhaustion_minutes is not None else None,
            "r_squared": round(self.r_squared, 3),
            "warning_level": self.warning_level,
            "trend_model": self.trend_model,
            "sample_count": self.sample_count,
            "forecast_points": [p.to_dict() for p in self.forecast_points],
        }


class CapacityRiskSummary(BaseModel):
    """Synthesized capacity risk analysis and prescriptive SRE recommendations."""
    service_name: str
    highest_risk_metric: str
    current_metric_value: float
    shortest_tte_seconds: Optional[float]
    shortest_tte_minutes: Optional[float]
    overall_risk_score: float  # 0.0 (safest) to 100.0 (highest exhaustion hazard)
    risk_tier: str  # HEALTHY, LOW, MODERATE, HIGH, CRITICAL
    recommendations: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "highest_risk_metric": self.highest_risk_metric,
            "current_metric_value": round(self.current_metric_value, 2),
            "shortest_tte_seconds": round(self.shortest_tte_seconds, 1) if self.shortest_tte_seconds is not None else None,
            "shortest_tte_minutes": round(self.shortest_tte_minutes, 1) if self.shortest_tte_minutes is not None else None,
            "overall_risk_score": round(self.overall_risk_score, 1),
            "risk_tier": self.risk_tier,
            "recommendations": self.recommendations,
        }
