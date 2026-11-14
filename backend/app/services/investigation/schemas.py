"""
INCIDENTX AI - Investigation Domain Pydantic Schemas
Defines structured input and output schemas for all 10 specialized investigation agents.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# 1. Incident Intake Agent Schemas
# -------------------------------------------------------------
class IntakeResult(BaseModel):
    is_valid: bool = True
    incident_id: str
    normalized_severity: str = "SEV-2"
    normalized_scope: List[str] = Field(default_factory=list)
    initial_assessment: str = ""
    sanitization_applied: bool = True


# -------------------------------------------------------------
# 2. Context Gathering Agent Schemas
# -------------------------------------------------------------
class ServiceContext(BaseModel):
    service_id: str
    name: str
    tier: str
    service_type: str
    language: Optional[str] = None
    health_status: str
    dependencies: List[str] = Field(default_factory=list)


class ContextResult(BaseModel):
    services_metadata: Dict[str, ServiceContext] = Field(default_factory=dict)
    topology_depth: int = 1
    upstream_callers: List[str] = Field(default_factory=list)
    downstream_callees: List[str] = Field(default_factory=list)
    critical_path: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# 3. Telemetry Analysis Agent Schemas
# -------------------------------------------------------------
class MetricAnomalyDetail(BaseModel):
    service_name: str
    metric_name: str
    current_value: float
    baseline_value: float
    deviation_sigma: Optional[float] = None
    severity: str
    observation: str


class TelemetryAnalysisResult(BaseModel):
    anomalous_metrics: List[MetricAnomalyDetail] = Field(default_factory=list)
    peak_saturation_services: List[str] = Field(default_factory=list)
    first_metric_breach_timestamp: Optional[str] = None
    telemetry_summary: str = ""


# -------------------------------------------------------------
# 4. Log Analysis Agent Schemas
# -------------------------------------------------------------
class LogExceptionCluster(BaseModel):
    service_name: str
    signature: str
    count: int
    first_seen: str
    sample_message: str


class LogAnalysisResult(BaseModel):
    exception_clusters: List[LogExceptionCluster] = Field(default_factory=list)
    fatal_errors_count: int = 0
    prompt_injection_detected: bool = False
    log_summary: str = ""


# -------------------------------------------------------------
# 5. Trace Analysis Agent Schemas
# -------------------------------------------------------------
class TraceSpanFailure(BaseModel):
    trace_id: str
    span_id: str
    service_name: str
    operation_name: str
    duration_ms: float
    status_code: int
    error_message: Optional[str] = None


class TraceAnalysisResult(BaseModel):
    failed_traces_count: int = 0
    slowest_spans: List[TraceSpanFailure] = Field(default_factory=list)
    root_cause_span_service: Optional[str] = None
    waterfall_bottleneck_summary: str = ""


# -------------------------------------------------------------
# 6. Service Dependency Analysis Agent Schemas
# -------------------------------------------------------------
class DependencyAnalysisResult(BaseModel):
    causal_origin_service: str
    propagation_chain: List[str] = Field(default_factory=list)
    blast_radius: List[str] = Field(default_factory=list)
    is_downstream_symptom: bool = False
    causal_explanation: str = ""


# -------------------------------------------------------------
# 7. Deployment & Configuration Change Agent Schemas
# -------------------------------------------------------------
class DeploymentRecord(BaseModel):
    service_name: str
    version: str
    deployed_at: str
    commit_sha: Optional[str] = None
    change_type: str = "RELEASE"
    is_suspicious: bool = False


class DeploymentAnalysisResult(BaseModel):
    deployments_detected: List[DeploymentRecord] = Field(default_factory=list)
    config_changes_detected: List[str] = Field(default_factory=list)
    temporal_correlation_score: float = 0.0
    deployment_impact_summary: str = ""


# -------------------------------------------------------------
# 8. Root Cause Hypothesis Agent Schemas (Courtroom Format)
# -------------------------------------------------------------
class ProposedHypothesis(BaseModel):
    culprit_service: str
    title: str
    hypothesis_text: str
    initial_probability: float
    prosecutor_argument: str
    defense_argument: str
    causal_mechanism: str


class HypothesisGenerationResult(BaseModel):
    competing_hypotheses: List[ProposedHypothesis] = Field(default_factory=list)
    generation_rationale: str = ""


# -------------------------------------------------------------
# 9. Evidence Verification Agent Schemas
# -------------------------------------------------------------
class VerifiedHypothesisEvaluation(BaseModel):
    hypothesis_title: str
    culprit_service: str
    confidence_score: float
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    status: str  # VALIDATED, UNDER_CROSS_EXAMINATION, DISPROVEN, INSUFFICIENT_EVIDENCE
    judicial_ruling: str


class VerificationResult(BaseModel):
    evaluations: List[VerifiedHypothesisEvaluation] = Field(default_factory=list)
    highest_confidence_hypothesis: Optional[VerifiedHypothesisEvaluation] = None
    evidence_sufficiency_verdict: str = "SUFFICIENT"


# -------------------------------------------------------------
# 10. Investigation Summary & Active Planner Schemas
# -------------------------------------------------------------
class DiagnosticAction(BaseModel):
    action_id: str
    name: str
    category: str
    target_service: str
    diagnostic_value: float  # 0.0 to 1.0
    estimated_cost: str  # LOW, MEDIUM, HIGH
    operational_risk: str  # LOW, MEDIUM, HIGH (Strictly safe actions)
    rationale: str


class InvestigationSummaryResult(BaseModel):
    executive_summary: str
    root_cause_ruling: str
    confidence_score: float
    identified_culprit: str
    causal_reconstruction: List[str] = Field(default_factory=list)
    recommended_diagnostic_actions: List[DiagnosticAction] = Field(default_factory=list)
    evidence_provenance_count: int = 0


# -------------------------------------------------------------
# 11. Kubernetes Infrastructure Investigator Agent Schemas
# -------------------------------------------------------------
class KubernetesPodDiagnostic(BaseModel):
    pod_name: str
    namespace: str
    phase: str
    restart_count: int
    exit_code: Optional[int] = None
    exit_reason: Optional[str] = None
    node_name: Optional[str] = None
    is_crashloop: bool = False
    is_oomkilled: bool = False


class KubernetesNodeDiagnostic(BaseModel):
    node_name: str
    ready: bool
    memory_pressure: bool = False
    disk_pressure: bool = False
    pid_pressure: bool = False


class KubernetesDiagnosticResult(BaseModel):
    environment_mode: str
    cluster_reachable: bool = True
    pod_diagnostics: List[KubernetesPodDiagnostic] = Field(default_factory=list)
    node_diagnostics: List[KubernetesNodeDiagnostic] = Field(default_factory=list)
    warning_events_count: int = 0
    oomkilled_count: int = 0
    crashloop_count: int = 0
    infrastructure_culprit_service: Optional[str] = None
    infrastructure_summary: str = ""

