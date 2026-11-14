"""
INCIDENTX AI - Recovery Verification & Self-Learning Schemas (Phase 13)
Data contracts for recovery verification, before/after telemetry comparison,
stability monitoring, postmortems, incident knowledge, and continuous learning.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# MODULE 13.1 & 13.3 — RECOVERY STATUSES & CRITERIA
# ============================================================================

class RecoveryStatus(str, Enum):
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERY_SUCCESSFUL = "RECOVERY_SUCCESSFUL"
    RECOVERY_PARTIAL = "RECOVERY_PARTIAL"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    RECOVERY_REGRESSION = "RECOVERY_REGRESSION"


class RecoveryCriteria(BaseModel):
    """Configurable service-specific recovery thresholds."""
    service_name: str
    min_pod_readiness_ratio: float = 1.0       # 100% of replicas ready
    max_5xx_error_rate_percent: float = 2.0    # < 2.0%
    max_p95_latency_ms: float = 300.0          # < 300ms
    max_p99_latency_ms: float = 800.0          # < 800ms
    max_cpu_percent: float = 80.0              # < 80%
    max_memory_percent: float = 80.0           # < 80%
    max_recent_restarts: int = 0               # 0 new restarts post-remediation
    require_database_healthy: bool = True
    require_dependencies_healthy: bool = True
    min_observation_seconds: int = 300         # 5 min default observation window


# ============================================================================
# MODULE 13.2 — BEFORE-AND-AFTER TELEMETRY COMPARISON
# ============================================================================

class TelemetryStage(str, Enum):
    BEFORE = "BEFORE"
    DURING = "DURING"
    AFTER = "AFTER"


class TelemetrySnapshot(BaseModel):
    """Point-in-time telemetry snapshot for a service."""
    snapshot_id: str
    incident_id: str
    service_name: str
    environment: str = "DEMOMESH"
    stage: TelemetryStage
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Pod / Container
    replicas_desired: int = 2
    replicas_ready: int = 2
    restart_count: int = 0
    pod_readiness_ratio: float = 1.0
    
    # Application / HTTP
    error_rate_percent: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    throughput_rps: Optional[float] = None
    
    # System Resources
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    
    # Dependencies & Database
    db_query_latency_ms: Optional[float] = None
    db_pool_utilization_percent: Optional[float] = None
    dependency_failure_rate_percent: Optional[float] = None
    network_drop_rate_percent: Optional[float] = None
    
    # Metadata
    is_simulated: bool = False
    raw_metrics: Dict[str, Any] = Field(default_factory=dict)


class MetricTrend(str, Enum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"
    UNKNOWN = "UNKNOWN"


class TelemetryMetricDiff(BaseModel):
    """Detailed diff for a single telemetry metric."""
    metric_name: str
    unit: str
    before_value: Optional[float] = None
    during_value: Optional[float] = None
    after_value: Optional[float] = None
    delta_value: Optional[float] = None
    percentage_change: Optional[float] = None
    trend: MetricTrend = MetricTrend.UNKNOWN
    threshold: Optional[float] = None
    is_healthy: bool = True
    baseline_present: bool = True
    evaluation_notes: str = ""


class TelemetryComparisonReport(BaseModel):
    """Comprehensive comparison between before, during, and after telemetry."""
    comparison_id: str
    incident_id: str
    service_name: str
    environment: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metric Comparisons
    metrics: List[TelemetryMetricDiff] = Field(default_factory=list)
    
    # Summary Insights
    overall_trend: MetricTrend = MetricTrend.IMPROVED
    regression_detected: bool = False
    regressed_metrics: List[str] = Field(default_factory=list)
    improved_metrics: List[str] = Field(default_factory=list)
    unchanged_metrics: List[str] = Field(default_factory=list)
    
    # Honesty & Baseline Integrity
    baseline_incomplete: bool = False
    missing_metrics: List[str] = Field(default_factory=list)
    recovery_stability_score: float = 1.0  # 0.0 - 1.0
    summary: str = ""


# ============================================================================
# MODULE 13.1 & 13.3 — ADVANCED RECOVERY VERIFICATION & STABILITY MONITOR
# ============================================================================

class AdvancedRecoveryReport(BaseModel):
    """Comprehensive recovery verification assessment."""
    verification_id: str
    incident_id: str
    service_name: str
    environment: str
    status: RecoveryStatus
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Detailed Pillar Statuses
    pod_readiness_verified: bool = True
    deployment_available: bool = True
    restart_frequency_cleared: bool = True
    error_rate_recovered: bool = True
    latency_normalized: bool = True
    resources_healthy: bool = True
    database_healthy: bool = True
    dependencies_healthy: bool = True
    distributed_trace_healthy: bool = True
    
    # Criteria & Measurements
    criteria_used: RecoveryCriteria
    telemetry_comparison: Optional[TelemetryComparisonReport] = None
    evidence_points: List[str] = Field(default_factory=list)
    failing_reasons: List[str] = Field(default_factory=list)
    requires_escalation: bool = False
    summary: str = ""


class StabilityCheckPoint(BaseModel):
    """Observation sample taken at an interval inside an observation window."""
    check_index: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_rate_percent: float
    p95_latency_ms: float
    replicas_ready: int
    restart_count: int
    is_healthy: bool
    drift_detected: bool = False


class RecoveryStabilityReport(BaseModel):
    """Multi-window stability monitor results."""
    stability_id: str
    incident_id: str
    service_name: str
    observation_window_seconds: int = 300  # e.g., 5 min, 15 min
    check_interval_seconds: int = 60
    total_checks_performed: int = 0
    checks: List[StabilityCheckPoint] = Field(default_factory=list)
    
    is_stable: bool = True
    regression_detected: bool = False
    escalation_triggered: bool = False
    status: RecoveryStatus = RecoveryStatus.RECOVERY_SUCCESSFUL
    stability_confidence: float = 1.0  # 0.0 - 1.0
    notes: str = ""
    last_checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# MODULE 13.4 — AUTOMATED POSTMORTEM GENERATION
# ============================================================================

class PostmortemTask(BaseModel):
    """Actionable preventive or follow-up task."""
    task_id: str
    title: str
    description: str
    owner: str = "SRE_TEAM"
    priority: str = "P2"  # P1, P2, P3
    status: str = "OPEN"
    due_date: Optional[str] = None


class PostmortemReport(BaseModel):
    """Professional incident postmortem document."""
    postmortem_id: str
    incident_id: str
    title: str
    severity: str
    environment: str
    affected_services: List[str] = Field(default_factory=list)
    
    # Timing
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    remediated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    incident_duration_minutes: float = 0.0
    detection_method: str = "PROMETHEUS_ALERT"
    
    # Root Cause & Causal Analysis (Facts vs Interpretation)
    verified_root_cause: str
    root_cause_is_conclusive: bool = True
    contributing_factors: List[str] = Field(default_factory=list)
    verified_facts: List[str] = Field(default_factory=list)
    ai_interpretations: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    counter_evidence: List[str] = Field(default_factory=list)
    
    # Actions & Approval
    remediation_performed: str
    approval_details: Dict[str, Any] = Field(default_factory=dict)
    rollback_occurred: bool = False
    
    # Recovery & Telemetry
    recovery_status: str
    recovery_summary: str
    before_after_telemetry: Optional[TelemetryComparisonReport] = None
    
    # Impact & Future Prevention
    customer_impact_summary: str = "Internal simulated service degradation. No external customers impacted."
    lessons_learned: List[str] = Field(default_factory=list)
    preventive_actions: List[str] = Field(default_factory=list)
    follow_up_tasks: List[PostmortemTask] = Field(default_factory=list)
    
    # Investigation Timeline
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    author: str = "IncidentX AI Postmortem Generator"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    markdown_content: str = ""
    html_content: str = ""


# ============================================================================
# MODULE 13.5 — INCIDENT KNOWLEDGE ENGINE
# ============================================================================

class IncidentKnowledgeEntry(BaseModel):
    """Searchable historical knowledge entry."""
    incident_id: str
    title: str
    severity: str
    affected_services: List[str]
    environment: str
    
    # Fingerprint & Signatures
    incident_fingerprint: str
    error_signature: str
    root_cause_category: str
    verified_root_cause: str
    deployment_sha: Optional[str] = None
    
    # Telemetry & Resolution
    key_metrics_impacted: List[str] = Field(default_factory=list)
    effective_remediations: List[str] = Field(default_factory=list)
    failed_remediations: List[str] = Field(default_factory=list)
    recovery_status: str = "RECOVERY_SUCCESSFUL"
    postmortem_id: Optional[str] = None
    
    # Learning & Integrity
    is_verified_by_human: bool = False
    learning_weight: float = 1.0
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SimilarIncidentMatch(BaseModel):
    """Result of searching the historical knowledge base."""
    incident_id: str
    title: str
    severity: str
    similarity_score: float  # 0.0 - 1.0
    matching_features: List[str] = Field(default_factory=list)
    common_services: List[str] = Field(default_factory=list)
    verified_root_cause: str
    recommended_remediations: List[str] = Field(default_factory=list)
    postmortem_id: Optional[str] = None


class FailurePattern(BaseModel):
    """Detected recurring failure pattern across incidents."""
    pattern_id: str
    pattern_name: str
    frequency_count: int
    affected_services: List[str]
    common_root_cause: str
    error_signature: str
    mean_time_to_detect_minutes: float = 0.0
    mean_time_to_recover_minutes: float = 0.0
    recommended_systemic_fix: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# MODULE 13.6 — CONTROLLED SELF-LEARNING & INVESTIGATION IMPROVEMENT
# ============================================================================

class LearningPolicyChange(BaseModel):
    """Versioned and reversible learning update."""
    version_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_incident_ids: List[str] = Field(default_factory=list)
    
    # Weight & Priority Adjustments
    hypothesis_ranking_weights: Dict[str, float] = Field(default_factory=dict)
    agent_task_priorities: Dict[str, int] = Field(default_factory=dict)
    evidence_collection_weights: Dict[str, float] = Field(default_factory=dict)
    
    # Audit & Reversibility
    rationale: str
    human_approved: bool = False
    approved_by: Optional[str] = None
    is_active: bool = True
    previous_version_id: Optional[str] = None


class HumanFeedback(BaseModel):
    """Human feedback on an investigation, root cause, or remediation."""
    feedback_id: str
    incident_id: str
    reviewer: str = "oncall-engineer"
    reviewer_role: str = "SRE_LEAD"
    rating: int = 5  # 1-5
    root_cause_accurate: bool = True
    remediation_effective: bool = True
    corrected_root_cause: Optional[str] = None
    comments: str = ""
    approved_learning_update: bool = True
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# MODULE 13.7 — CONTINUOUS IMPROVEMENT RECOMMENDATIONS
# ============================================================================

class RecommendationCategory(str, Enum):
    MONITORING = "MONITORING"
    ALERTS = "ALERTS"
    HEALTH_CHECKS = "HEALTH_CHECKS"
    RESOURCE_LIMITS = "RESOURCE_LIMITS"
    DEPLOYMENT_SAFEGUARDS = "DEPLOYMENT_SAFEGUARDS"
    DEPENDENCY_OBSERVABILITY = "DEPENDENCY_OBSERVABILITY"
    ESCALATION_POLICIES = "ESCALATION_POLICIES"


class ContinuousImprovementRecommendation(BaseModel):
    """Actionable improvement recommendation to prevent future failures."""
    recommendation_id: str
    incident_id: str
    category: RecommendationCategory
    title: str
    description: str
    supporting_evidence: List[str] = Field(default_factory=list)
    expected_benefit: str
    priority: str = "P2"       # P1, P2, P3
    complexity: str = "MEDIUM" # LOW, MEDIUM, HIGH
    risk: str = "LOW"          # LOW, MEDIUM, HIGH
    suggested_owner: str = "Core SRE Team"
    verification_criteria: str
    status: str = "OPEN"       # OPEN, ACCEPTED, IMPLEMENTED, REJECTED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
