"""
INCIDENTX AI - Advanced SRE Intelligence Engine Schemas (Phase 15)
Data contracts for anomaly detection, incident prediction, service health,
SLO / error budgets, deployment correlation, and cascading failure intelligence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyClassification(str, Enum):
    NORMAL = "NORMAL"
    UNUSUAL = "UNUSUAL"
    CONFIRMED_ANOMALY = "CONFIRMED_ANOMALY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RiskCategory(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ServiceHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AnomalySignal(BaseModel):
    """Single metric anomaly evaluation."""
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    classification: AnomalyClassification
    unit: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MultiSignalAnomalyReport(BaseModel):
    """Comprehensive anomaly report across all telemetry signals for a service."""
    report_id: str
    service_name: str
    overall_classification: AnomalyClassification
    multivariate_anomaly_score: float  # 0.0 - 1.0
    anomalous_signals: List[AnomalySignal] = Field(default_factory=list)
    evaluated_signals_count: int = 0
    summary: str = ""
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PredictedIncidentRisk(BaseModel):
    """Early-warning incident prediction."""
    prediction_id: str
    service_name: str
    risk_category: RiskCategory
    risk_type: str  # MEMORY_EXHAUSTION, CPU_SATURATION, API_LATENCY_SPIKE, CASCADING_FAILURE
    confidence_score: float  # 0.0 - 1.0
    predicted_lead_time_minutes: float  # e.g., 15.0 min
    supporting_signals: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    recommended_proactive_investigation: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceHealthOverview(BaseModel):
    """Real-time health breakdown for a microservice."""
    service_name: str
    health_status: ServiceHealthStatus
    availability_percent: float = 100.0
    p95_latency_ms: float = 45.0
    error_rate_percent: float = 0.02
    cpu_saturation_percent: float = 35.0
    memory_saturation_percent: float = 42.0
    active_anomalies_count: int = 0
    slo_status: str = "COMPLIANT"
    explanation: str = "All golden signals within nominal SLA boundaries."
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SLOTarget(BaseModel):
    """Service Level Objective and Error Budget model."""
    slo_id: str
    service_name: str
    slo_name: str  # e.g., "99.9% API Availability", "P95 Latency < 300ms"
    target_percent: float = 99.9
    current_percent: float = 99.95
    error_budget_total_minutes: float = 43.2
    error_budget_remaining_percent: float = 88.5
    error_budget_consumed_percent: float = 11.5
    burn_rate: float = 1.0  # 1x normal, 6x fast, 14.4x critical
    burn_rate_status: str = "NORMAL"  # NORMAL, ELEVATED, CRITICAL_BURN
    measurement_window: str = "30d"
    is_breached: bool = False


class DeploymentRiskAssessment(BaseModel):
    """Correlation between recent software release and service health."""
    deployment_id: str
    service_name: str
    git_sha: str
    deployed_at: datetime
    risk_score: float  # 0.0 - 1.0
    risk_category: RiskCategory
    is_correlated_with_degradation: bool = False
    telemetry_changes: List[str] = Field(default_factory=list)
    explanation: str = ""
    suggested_verification: str = "Run canary test suite and compare error rate with previous revision."


class CascadingFailureRisk(BaseModel):
    """Impact graph evaluation across service dependencies."""
    root_service: str
    downstream_impacted_services: List[str] = Field(default_factory=list)
    bottleneck_service: str
    blast_radius_score: float  # 0.0 - 1.0
    potential_impact: str = "High risk of cascading timeouts to checkout gateway"
    mitigation_recommendation: str = "Enable upstream circuit breaker to shed load."


class PredictiveRecommendation(BaseModel):
    """Proactive recommendation to avert impending incident."""
    recommendation_id: str
    service_name: str
    priority: str = "P2"
    risk: str = "LOW"
    suggested_action: str
    expected_outcome: str
    verification_method: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelEvaluationMetrics(BaseModel):
    """Metrics tracking the predictive model precision and reliability."""
    model_version: str = "sre-intel-v1.4"
    anomaly_precision: float = 0.94
    false_positive_rate: float = 0.05
    prediction_accuracy: float = 0.89
    mean_lead_time_minutes: float = 14.2
    data_coverage_percent: float = 98.5
    evaluation_period: str = "Past 30 Days"
