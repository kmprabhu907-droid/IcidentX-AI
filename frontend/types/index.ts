export type Severity = "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4";
export type IncidentStatus = "DETECTED" | "INVESTIGATING" | "MITIGATING" | "RESOLVED" | "CLOSED";
export type HealthStatus = "HEALTHY" | "DEGRADED" | "CRITICAL";

export interface Incident {
  id: string;
  title: string;
  summary?: string | null;
  severity: Severity;
  status: IncidentStatus;
  detected_at: string;
  resolved_at?: string | null;
  impact_scope?: string | null;
  mttr_seconds?: number | null;
  created_at: string;
  updated_at: string;
}

export interface Service {
  id: string;
  name: string;
  tier: "Tier-1" | "Tier-2" | "Tier-3";
  service_type: "gateway" | "service" | "database" | "cache" | "queue" | "mesh";
  language?: string | null;
  health_status: HealthStatus;
  repository_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ServiceDependency {
  id: string;
  source_service_id: string;
  target_service_id: string;
  protocol: string;
  is_critical: boolean;
  created_at: string;
  updated_at: string;
}

export interface Evidence {
  id: string;
  incident_id: string;
  hypothesis_id?: string | null;
  evidence_type: string;
  source_system: string;
  affected_service_name?: string | null;
  raw_source_ref?: string | null;
  description: string;
  relevant_observation?: string | null;
  confidence_score: number;
  is_contradictory: boolean;
  verification_status?: string;
  observed_at: string;
  raw_data?: string | null;
  created_at: string;
}

export interface RootCauseHypothesis {
  id: string;
  incident_id: string;
  culprit_service_id?: string | null;
  hypothesis_text: string;
  probability_score: number;
  status: "PROPOSED" | "UNDER_CROSS_EXAMINATION" | "VALIDATED" | "DISPROVEN" | "INSUFFICIENT_EVIDENCE" | string;
  prosecutor_argument?: string | null;
  defense_argument?: string | null;
  judicial_ruling?: string | null;
  causal_chain?: string | null;
  missing_evidence?: string | null;
  evidence_count?: number;
  contradiction_count?: number;
  is_confirmed_root_cause: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentExecution {
  id: string;
  incident_id: string;
  agent_role: string;
  execution_phase: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | string;
  model_version?: string | null;
  prompt_version?: string | null;
  thought_process?: string | null;
  tool_name?: string | null;
  tool_arguments?: string | null;
  observation?: string | null;
  error_message?: string | null;
  duration_ms?: number | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  incident_id?: string | null;
  actor_type: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details?: string | null;
  ip_address?: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  components: {
    api: string;
    database: string;
  };
}

// ==========================================
// Phase 2: Observability & Telemetry Types
// ==========================================

export interface ClusterOverview {
  cluster_status: "HEALTHY" | "DEGRADED" | "CRITICAL";
  data_source: "LIVE" | "SIMULATED";
  total_request_rate: number;
  overall_error_rate: number;
  avg_p95_latency_ms: number;
  max_p95_latency_ms: number;
  total_services: number;
  healthy_services: number;
  degraded_services: number;
  critical_services: number;
  active_anomalies_count: number;
  timestamp: string;
}

export interface ServiceMetricSnapshot {
  timestamp: string;
  service_name: string;
  request_count: number;
  request_rate: number;
  error_count: number;
  error_rate: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  cpu_utilization: number;
  memory_utilization: number;
  db_pool_utilization: number;
  health_status: string;
  data_source: "LIVE" | "SIMULATED";
}

export interface Span {
  span_id: string;
  trace_id: string;
  service_name: string;
  name: string;
  operation_name?: string;
  parent_span_id?: string | null;
  start_offset_ms: number;
  duration_ms: number;
  status: "OK" | "ERROR";
  status_code: number;
  tags?: Record<string, any>;
  error_message?: string | null;
}

export interface Trace {
  trace_id: string;
  root_service: string;
  operation_name: string;
  start_time: string;
  duration_ms: number;
  status_code: number;
  has_error: boolean;
  data_source: "LIVE" | "SIMULATED";
  span_count: number;
  spans: Span[];
}

export interface LogRecord {
  id: string;
  timestamp: string;
  service_name: string;
  level: "INFO" | "WARN" | "ERROR" | "DEBUG";
  message: string;
  trace_id?: string | null;
  span_id?: string | null;
  context?: Record<string, any>;
  data_source: "LIVE" | "SIMULATED";
}

export interface AnomalyAlert {
  alert_id: string;
  detector_type: string;
  service_name: string;
  metric_name: string;
  current_value: number;
  threshold_or_baseline: number;
  severity: "INFO" | "WARN" | "CRITICAL";
  message: string;
  deviation_sigma?: number | null;
  context?: Record<string, any>;
  data_source: "LIVE" | "SIMULATED";
  timestamp: string;
}

export interface ChaosScenario {
  id: string;
  name: string;
  description: string;
  target_service: string;
  category: string;
  default_duration_seconds: number;
  impact_summary: string;
  severity_potential: string;
}

export interface ActiveFault {
  fault_id: string;
  scenario_id: string;
  target_service: string;
  duration_seconds: number;
  elapsed_seconds: number;
  remaining_seconds: number;
  parameters: Record<string, any>;
  started_at: string;
  data_source: "SIMULATED";
}

export interface SimulationStatus {
  is_active: boolean;
  active_fault_count: number;
  data_source: "LIVE" | "SIMULATED";
  active_faults: ActiveFault[];
}

// ==========================================
// Phase 3: Investigation, Courtroom & Timeline Types
// ==========================================

export interface TimelineEvent {
  id: string;
  incident_id: string;
  timestamp: string;
  event_type: string;
  service_name: string;
  title: string;
  description: string;
  severity: string;
  data_source: string;
  raw_data?: string | null;
  created_at: string;
}

export interface CourtroomItem {
  hypothesis: RootCauseHypothesis;
  supporting_evidence: Evidence[];
  contradictory_evidence: Evidence[];
  judicial_ruling?: string | null;
  is_insufficient_evidence: boolean;
}

export interface CourtroomView {
  incident_id: string;
  incident_title: string;
  severity: string;
  total_hypotheses: number;
  courtroom_evaluations: CourtroomItem[];
}

export interface DiagnosticAction {
  action_id: string;
  name: string;
  category?: string;
  target_service: string;
  safety_rating?: "SAFE" | "RESTRICTED" | "HAZARDOUS" | string;
  operational_risk?: "LOW" | "MEDIUM" | "HIGH" | string;
  command_type?: "READ_ONLY" | "PROBE" | "INSPECTION" | string;
  diagnostic_value?: number;
  value_estimate?: string;
  estimated_cost: string;
  risk_explanation?: string;
  command_template?: string;
  rationale?: string;
  justification?: string;
}

export interface InvestigationPlanView {
  incident_id: string;
  plan_status: string;
  total_actions: number;
  recommended_actions: DiagnosticAction[];
}

export interface InvestigationStatus {
  incident_id: string;
  current_stage: string;
  status: string;
  completed_agents: string[];
  failed_agents: string[];
  duration_ms: number;
}

export interface TimelineView {
  incident_id: string;
  total_events: number;
  events: TimelineEvent[];
}

// ==========================================
// Phase 4: Safe Autonomous Remediation & Self-Healing Types
// ==========================================

export type ExecutionMode = "RECOMMENDATION_ONLY" | "HUMAN_APPROVAL" | "CONTROLLED_AUTONOMOUS";
export type ActionRiskLevel = "LOW" | "MEDIUM" | "HIGH";
export type ActionStatus = "PROPOSED" | "APPROVED" | "REJECTED" | "EXECUTING" | "EXECUTED" | "FAILED" | "CANCELLED";
export type ActionApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | "NOT_REQUIRED";
export type RecoveryVerificationStatus = "PENDING" | "VERIFIED" | "PARTIALLY_VERIFIED" | "FAILED" | "INCONCLUSIVE";
export type ActionRollbackStatus = "NONE" | "AVAILABLE" | "EXECUTING" | "ROLLED_BACK" | "ROLLBACK_FAILED";

export interface RemediationAction {
  id: string;
  incident_id: string;
  hypothesis_id?: string | null;
  action_id: string;
  name: string;
  description: string;
  action_type: string;
  target_service_name: string;
  parameters: string;
  preconditions: string;
  expected_outcome: string;
  risk_level: ActionRiskLevel;
  risk_tier: string;
  estimated_cost: string;
  expected_benefit: number;
  recommendation_reason: string;
  contraindications: string;
  execution_mode: ExecutionMode;
  idempotency_key: string;
  timeout_seconds: number;
  approval_status: ActionApprovalStatus;
  approved_by?: string | null;
  approved_at?: string | null;
  approval_comment?: string | null;
  status: ActionStatus;
  command_payload: string;
  executed_at?: string | null;
  execution_duration_ms?: number | null;
  execution_log?: string | null;
  snapshot_before?: string | null;
  snapshot_after?: string | null;
  verification_status: RecoveryVerificationStatus;
  verification_details?: string | null;
  rollback_status: ActionRollbackStatus;
  rollback_log?: string | null;
  error_message?: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface RemediationPolicy {
  id: string;
  name: string;
  mode: ExecutionMode;
  is_autonomous_enabled: boolean;
  allowlisted_action_ids: string;
  max_actions_per_incident: number;
  max_retries: number;
  cooldown_seconds: number;
  circuit_breaker_tripped: boolean;
  circuit_breaker_reason?: string | null;
  emergency_stop_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActionRegistryItem {
  action_id: string;
  name: string;
  description: string;
  action_type: string;
  supported_incident_types: string[];
  risk_level: ActionRiskLevel;
  estimated_cost: string;
  timeout_seconds: number;
  parameter_schema: Record<string, any>;
}

export interface MetricDelta {
  before: number;
  after: number;
  delta: number;
}

export interface VerificationReport {
  service_name: string;
  verification_status: RecoveryVerificationStatus;
  metrics: {
    error_rate: MetricDelta;
    latency_p95_ms: MetricDelta;
    cpu_utilization: MetricDelta;
    memory_utilization: MetricDelta;
    db_pool_utilization: MetricDelta;
    health_status: { before: string; after: string };
  };
  is_recovery_confirmed: boolean;
  timestamp: string;
}

export interface RemediationRecommendationsResponse {
  incident_id: string;
  total_recommendations: number;
  actions: RemediationAction[];
  disclaimer: string;
}

// Stage 5.2 Anomaly & Resource Creep Types
export interface AnomalyRecordItem {
  id: string;
  service_id?: string | null;
  service_name: string;
  metric_name: string;
  observed_value: number;
  expected_baseline: number;
  deviation: number;
  ewma_value?: number | null;
  trend_slope?: number | null;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  confidence: number;
  detector_type: string;
  status: "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED" | "FALSE_POSITIVE";
  observation_count: number;
  first_observed_at?: string | null;
  last_observed_at?: string | null;
  detected_at?: string | null;
  data_source: string;
  supporting_evidence?: Record<string, any>;
  explanation?: {
    what_happened?: string;
    affected_service?: string;
    metric_changed?: string;
    normal_baseline?: string;
    deviation_magnitude?: string;
    duration_abnormal?: string;
    corroborating_signals?: string;
    confidence_assessment?: string;
    projected_impact?: string;
    next_investigation_step?: string;
  };
}

export interface MetricBaselineItem {
  service_name: string;
  metric_name: string;
  mean: number;
  std_dev: number;
  min_normal: number;
  max_normal: number;
  sample_count: number;
  has_sufficient_history: boolean;
}

export interface DetectionStatus {
  status: string;
  last_detection_cycle?: string | null;
  total_anomalies_detected: number;
  active_anomalies_count: number;
  monitored_services: number;
  last_error?: string | null;
}

// Stage 5.3 Regression Detection & Historical Failure Intelligence Types
export interface MetricStateValueItem {
  metric_name: string;
  unit: string;
  healthy_baseline: number;
  pre_incident: number;
  post_remediation: number;
  current_state: number;
  delta_failure: number;
  delta_recovery: number;
  delta_degradation: number;
  delta_total_departure: number;
  recovery_retained_ratio: number;
  is_regressing: boolean;
  status_summary: string;
}

export interface FourStateComparisonData {
  service_name: string;
  comparison_window_minutes: number;
  regressing_metrics: string[];
  recovered_metrics: string[];
  worsening_metrics: string[];
  overall_health_score: number;
  summary: string;
  metrics: Record<string, MetricStateValueItem>;
}

export interface SimilarityResultItem {
  overall_similarity_score: number;
  services_similarity: number;
  metric_vector_similarity: number;
  root_cause_similarity: number;
  topology_path_similarity: number;
  error_signature_similarity: number;
  weights_used: Record<string, number>;
  shared_services: string[];
  shared_metrics: string[];
  shared_root_causes: string[];
  shared_error_signatures: string[];
  explanation: string;
}

export interface RemediationReportItem {
  action_id: string;
  action_name: string;
  target_service_name: string;
  outcome: string;
  stability_score: number;
  immediate_verification_status: string;
  time_to_degradation_seconds?: number | null;
  re_abnormal_metrics: string[];
  secondary_degraded_metrics: string[];
  required_rollback: boolean;
  observation_window_minutes: number;
  sample_count: number;
  explanation: string;
}

export interface RegressionRecordItem {
  id: string;
  service_id?: string | null;
  service_name: string;
  incident_id?: string | null;
  current_incident_id?: string | null;
  metric_name: string;
  affected_services: string[];
  matching_incident_ids: string[];
  baseline_value: number;
  pre_incident_value?: number | null;
  post_remediation_value: number;
  current_value: number;
  similarity_score: number;
  regression_score: number;
  classification: "LOW_SIMILARITY" | "POSSIBLE_REGRESSION" | "LIKELY_REGRESSION" | "CONFIRMED_REGRESSION";
  status: "ACTIVE" | "INVESTIGATING" | "CONFIRMED" | "RESOLVED" | "FALSE_POSITIVE";
  evidence?: {
    detected_pattern?: string;
    similarity_result?: SimilarityResultItem;
    remediation_report?: RemediationReportItem;
    score_breakdown?: Record<string, number>;
  } | null;
  comparison_windows?: FourStateComparisonData | null;
  previous_remediation_ids: string[];
  details?: string | null;
  explanation?: {
    which_previous_incident?: string;
    affected_services?: string;
    metrics_returning_abnormal?: string;
    original_root_cause_hypothesis?: string;
    previous_remediation_performed?: string;
    did_remediation_provide_sustained_improvement?: string;
    evidence_supporting_recurrence?: string;
    evidence_contradicting_recurrence?: string;
    similarity_strength?: string;
    next_investigation_step?: string;
  } | null;
  data_source: string;
  first_observed_at?: string | null;
  last_observed_at?: string | null;
  detected_at?: string | null;
}

export interface RemediationEffectivenessOverview {
  total_remediations_analyzed: number;
  verified_immediately: number;
  rolled_back_count: number;
  execution_failed_count: number;
  active_regressions_count: number;
  remediation_stability_ratio: number;
  actions: Array<{
    id: string;
    action_id: string;
    name: string;
    target_service_name: string;
    verification_status: string;
    rollback_status: string;
    executed_at?: string | null;
  }>;
}
