export type Severity = "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4" | "P1" | "P2" | "P3" | "P4";
export type IncidentStatus =
  | "DETECTED"
  | "ACKNOWLEDGED"
  | "INVESTIGATING"
  | "ROOT_CAUSE_IDENTIFIED"
  | "REMEDIATION_PENDING"
  | "REMEDIATING"
  | "VERIFYING"
  | "RESOLVED"
  | "CLOSED"
  | "REOPENED"
  | "SUPPRESSED"
  | "CANCELLED"
  | "MITIGATING";
export type HealthStatus = "HEALTHY" | "DEGRADED" | "CRITICAL";

export interface Incident {
  id: string;
  title: string;
  summary?: string | null;
  severity: Severity;
  status: IncidentStatus;
  priority?: string | null;
  environment?: string | null;
  source?: string | null;
  fingerprint?: string | null;
  detected_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
  impact_scope?: string | null;
  mttr_seconds?: number | null;
  owner_id?: string | null;
  owner_name?: string | null;
  assigned_team?: string | null;
  oncall_responder?: string | null;
  escalation_status?: string | null;
  escalation_deadline?: string | null;
  is_escalated?: boolean;
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
  investigation_id?: string | null;
  hypothesis_id?: string | null;
  evidence_type: string;
  evidence_category?: string | null;
  source_system: string;
  source_agent?: string | null;
  affected_service_name?: string | null;
  raw_source_ref?: string | null;
  description: string;
  relevant_observation?: string | null;
  confidence_score: number;
  is_contradictory: boolean;
  is_fact?: boolean;
  environment?: string;
  deduplication_hash?: string | null;
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

// Phase 8.1 Dual-Environment Abstraction Types
export type EnvironmentMode = "DEMOMESH" | "KUBERNETES";

export interface EnvironmentMetadata {
  mode: EnvironmentMode;
  name: string;
  is_simulated: boolean;
  is_read_only: boolean;
  data_source: string;
  connected_at?: string | null;
  cluster_name?: string | null;
  cluster_version?: string | null;
  namespace?: string | null;
  node_count?: number | null;
  total_workloads: number;
  total_services: number;
}

export interface EnvironmentHealth {
  mode: EnvironmentMode;
  status: "CONNECTED" | "DISCONNECTED" | "ERROR" | "DEGRADED";
  is_healthy: boolean;
  active_incidents_or_faults: number;
  error_message?: string | null;
  latency_ms?: number | null;
  last_checked_at: string;
  data_source: string;
}

export interface InfrastructureWorkload {
  id: string;
  name: string;
  namespace: string;
  kind: string;
  replicas_desired: number;
  replicas_available: number;
  restart_count: number;
  phase: string;
  status: string;
  labels: Record<string, string>;
  data_source: string;
  created_at?: string | null;
}

export interface InfrastructureServiceItem {
  id: string;
  name: string;
  namespace: string;
  tier: string;
  endpoints: string[];
  protocol: string;
  data_source: string;
}

export interface InfrastructureEvent {
  id: string;
  timestamp: string;
  event_type: string;
  reason: string;
  message: string;
  source_component: string;
  resource_kind: string;
  resource_name: string;
  namespace?: string | null;
  count?: number;
  data_source: string;
}

export interface ResourceMetric {
  resource_id: string;
  resource_type: string;
  metric_name: string;
  value: number;
  unit: string;
  timestamp: string;
  data_source: string;
}

export interface EnvironmentSwitchResponse {
  message: string;
  previous_mode: string;
  active_mode: string;
  environment: EnvironmentMetadata;
}

// Phase 8.2 Kubernetes Cluster Integration Types
export interface KubernetesNode {
  name: string;
  ready: boolean;
  kubelet_version: string;
  os_image: string;
  architecture: string;
  cpu_allocatable_cores: number;
  memory_allocatable_mb: number;
  conditions: Record<string, string>;
  labels: Record<string, string>;
  creation_timestamp: string;
  data_source: string;
}

export interface KubernetesNamespace {
  name: string;
  status: string;
  workload_count: number;
  creation_timestamp: string;
  labels: Record<string, string>;
  data_source: string;
}

export interface KubernetesPod {
  name: string;
  namespace: string;
  phase: string;
  ready: boolean;
  restart_count: number;
  pod_ip?: string | null;
  node_name?: string | null;
  creation_timestamp: string;
  containers: Array<{
    name: string;
    ready: boolean;
    restart_count: number;
    image: string;
  }>;
  labels: Record<string, string>;
  data_source: string;
}

export interface KubernetesDeployment {
  name: string;
  namespace: string;
  desired_replicas: number;
  available_replicas: number;
  updated_replicas: number;
  rollout_status: string;
  conditions: any[];
  labels: Record<string, string>;
  creation_timestamp: string;
  data_source: string;
}

export interface KubernetesService {
  name: string;
  namespace: string;
  service_type: string;
  cluster_ip?: string | null;
  ports: Array<{
    name?: string;
    port: number;
    protocol: string;
    target_port?: number;
  }>;
  endpoints_available: number;
  selectors: Record<string, string>;
  creation_timestamp: string;
  data_source: string;
}

export interface KubernetesResourceMetrics {
  resource_type: string;
  resource_name: string;
  namespace?: string | null;
  configured_cpu_request_cores: number;
  configured_cpu_limit_cores: number;
  configured_memory_request_mb: number;
  configured_memory_limit_mb: number;
  measured_cpu_cores?: number | null;
  measured_memory_mb?: number | null;
  metrics_server_available: boolean;
  timestamp: string;
  data_source: string;
}

export interface KubernetesClusterOverview {
  connection_status: "CONNECTED" | "DISCONNECTED" | "ERROR";
  cluster_name: string;
  kubernetes_version: string;
  api_endpoint: string;
  auth_method: string;
  is_live: boolean;
  is_read_only: boolean;
  total_nodes: number;
  ready_nodes: number;
  total_namespaces: number;
  total_pods: number;
  healthy_deployments: number;
  metrics_server_available: boolean;
  error_message?: string | null;
  last_sync_timestamp: string;
  data_source: string;
}

export interface KubernetesConnectionDetails {
  cluster_id: string;
  cluster_name: string;
  api_server_url: string;
  auth_method: string;
  is_connected: boolean;
  is_live: boolean;
  is_read_only: boolean;
  masked_token?: string | null;
  discovered_version?: string | null;
  last_error?: string | null;
  connected_at?: string | null;
}

// -------------------------------------------------------------
// Phase 8.3: Live Observability (Prometheus, OpenTelemetry, Grafana)
// -------------------------------------------------------------
export interface PrometheusHealthStatus {
  status: "AVAILABLE" | "UNAVAILABLE" | "NOT_CONFIGURED" | "ERROR";
  endpoint: string;
  latency_ms: number;
  version?: string | null;
  error_message?: string | null;
  checked_at: string;
}

export interface PrometheusMetricSeries {
  metric_name: string;
  labels: Record<string, string>;
  values: [number, number][];
  latest_value?: number | null;
  unit: string;
}

export interface PrometheusQueryResult {
  status: "SUCCESS" | "UNAVAILABLE" | "ERROR" | "EMPTY";
  query: string;
  result_type: string;
  series: PrometheusMetricSeries[];
  error_message?: string | null;
  data_source: string;
  timestamp: string;
}

export interface PromQLTemplate {
  id: string;
  name: string;
  category: "CONTAINER" | "APPLICATION" | "NETWORK" | "KUBERNETES" | "NODE";
  description: string;
  query_template: string;
  unit: string;
  parameters: string[];
  default_step: string;
}

export interface OpenTelemetrySpan {
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  service_name: string;
  kind: string;
  start_time_iso: string;
  end_time_iso: string;
  duration_ms: number;
  status_code: string;
  status_message?: string | null;
  attributes: Record<string, any>;
  events: any[];
  k8s_namespace?: string | null;
  k8s_pod_name?: string | null;
  k8s_deployment_name?: string | null;
  incident_id?: string | null;
  is_bottleneck: boolean;
  is_error: boolean;
  data_source: string;
}

export interface OpenTelemetryTrace {
  trace_id: string;
  root_service: string;
  root_operation: string;
  start_time_iso: string;
  duration_ms: number;
  span_count: number;
  error_count: number;
  has_error: boolean;
  spans: OpenTelemetrySpan[];
  incident_id?: string | null;
  bottleneck_span_id?: string | null;
  data_source: string;
}

export interface GrafanaDashboardInfo {
  uid: string;
  title: string;
  url: string;
  tags: string[];
  type: string;
  is_starred: boolean;
}

export interface GrafanaAnnotation {
  id?: number | null;
  dashboard_uid?: string | null;
  time_ms: number;
  time_end_ms?: number | null;
  tags: string[];
  text: string;
  created_at?: string | null;
}

export interface UnifiedTelemetryTimelineItem {
  id: string;
  timestamp: string;
  source: "PROMETHEUS" | "OPENTELEMETRY" | "KUBERNETES" | "DEMOMESH" | "INCIDENT";
  category: "METRIC_ANOMALY" | "TRACE_FAILURE" | "K8S_EVENT" | "APPLICATION_LOG" | "INCIDENT_STATE";
  severity: "INFO" | "WARN" | "HIGH" | "CRITICAL";
  resource_name: string;
  message: string;
  details: Record<string, any>;
  data_source: "LIVE_K8S" | "SIMULATED";
  incident_id?: string | null;
}

export interface TelemetryAnomalyRecord {
  id: string;
  timestamp: string;
  metric_name: string;
  resource_name: string;
  detector_type: "STATIC_THRESHOLD" | "ROLLING_BASELINE" | "Z_SCORE";
  current_value: number;
  baseline_value: number;
  threshold_value: number;
  deviation_sigma?: number | null;
  consecutive_breaches: number;
  severity: "INFO" | "WARN" | "HIGH" | "CRITICAL";
  explanation: string;
  data_source: string;
}

export interface ObservabilityStackStatus {
  status: "HEALTHY" | "DEGRADED" | "UNHEALTHY";
  prometheus: PrometheusHealthStatus;
  opentelemetry: {
    status: string;
    buffered_traces_count: number;
    total_ingested_spans: number;
    total_ingested_traces: number;
  };
  grafana: {
    status: string;
    endpoint: string;
    latency_ms: number;
    version?: string | null;
    error_message?: string | null;
  };
  active_environment_mode: string;
  timestamp: string;
}




// Phase 8.4 AI Reasoning & Multi-Provider Models

export interface ProviderHealth {
  provider_name: string;
  status: "AVAILABLE" | "DEGRADED" | "UNAVAILABLE" | "NOT_CONFIGURED" | "ERROR";
  latency_ms: number;
  discovered_models?: string[];
  error_message?: string | null;
  checked_at: string;
}

export interface ProviderInfo {
  provider_name: string;
  display_name: string;
  configured: boolean;
  default_model: string;
  is_primary: boolean;
  is_secondary: boolean;
  is_fallback: boolean;
  circuit_breaker_tripped: boolean;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface ModelAttribution {
  provider_name: string;
  model_name: string;
  is_fallback: boolean;
  execution_time_ms: number;
  token_usage?: TokenUsage;
  timestamp: string;
}

export interface AIReasoningEvidenceItem {
  evidence_id: string;
  source_type: string;
  statement_classification: "OBSERVED_FACT" | "DERIVED_CALCULATION" | "STATISTICAL_INFERENCE";
  resource_name: string;
  timestamp: string;
  details: Record<string, any>;
  data_source: "LIVE_K8S" | "SIMULATED";
  is_valid: boolean;
}

export interface CourtroomHypothesis {
  hypothesis_id: string;
  culprit_service?: string;
  title: string;
  explanation: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  missing_evidence: string[];
  confidence_score: number;
  is_leading: boolean;
  verification_status: "PROPOSED" | "INVESTIGATED" | "VERIFIED" | "REJECTED" | "SUPERSEDED";
  recommended_action?: Record<string, any> | null;
}

export interface CourtroomVerdict {
  leading_hypothesis_id: string;
  verdict_summary: string;
  competing_hypotheses: CourtroomHypothesis[];
  counter_evidence_considered: string[];
  evidentiary_justification: string;
  confidence_score: number;
  confidence_limitations: string[];
  model_attribution: ModelAttribution;
}

export interface AIIncidentReasoningReport {
  incident_id: string;
  status: string;
  evidence_items: AIReasoningEvidenceItem[];
  courtroom_verdict: CourtroomVerdict;
  recommended_actions: Record<string, any>[];
  model_attribution: ModelAttribution;
  created_at: string;
}

export interface AIUsageRecord {
  id: string;
  incident_id?: string | null;
  agent_name: string;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  is_fallback: boolean;
  status: string;
  timestamp: string;
}

export interface AIUsageSummary {
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  average_latency_ms: number;
  fallback_count: number;
  daily_token_budget: number;
  budget_consumed_percent: number;
  usage_by_provider: Record<string, { requests: number; tokens: number; cost_usd: number }>;
  usage_by_model: Record<string, { requests: number; tokens: number; cost_usd: number }>;
}

export interface CircuitBreakerStatus {
  failure_count: number;
  is_tripped: boolean;
  max_failures: number;
  cooldown_seconds: number;
  last_failure_time: number;
}

// On-Call Incident Agent Models

export interface PageAlert {
  page_id: string;
  incident_id?: string | null;
  service_name: string;
  severity: "SEV-1" | "SEV-2" | "SEV-3" | "SEV-4";
  source: string;
  summary: string;
  paged_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  mtta_seconds?: number | null;
  status: "PAGED" | "ACKNOWLEDGED" | "TRIAGED" | "ESCALATED" | "RESOLVED";
  triage_summary?: string | null;
  confidence_score?: number | null;
  leading_root_cause?: string | null;
  recommended_action?: Record<string, any> | null;
  escalated_to?: string | null;
  escalation_reason?: string | null;
}

export interface OnCallShiftStatus {
  shift_id: string;
  primary_responder: string;
  secondary_responder: string;
  duty_status: string;
  shift_started_at: string;
  total_pages_handled: number;
  mean_time_to_acknowledge_seconds: number;
  escalation_rate_percent: number;
  active_pages_count: number;
}

// Phase 9: Intelligent On-Call Incident Command Center Types

export interface IncidentStatistics {
  total_active: number;
  p1_critical: number;
  p2_high: number;
  p3_medium: number;
  p4_low: number;
  investigating: number;
  unassigned: number;
  resolved_count: number;
  mean_time_to_acknowledge_seconds: number;
  mean_time_to_resolve_seconds: number;
  environment_counts: Record<string, number>;
}

export interface AlertRecord {
  id: string;
  incident_id?: string | null;
  fingerprint: string;
  source: string;
  alert_name: string;
  service_name: string;
  severity: string;
  environment: string;
  status: string;
  description?: string | null;
  occurrence_count: number;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface AlertIngestPayload {
  source?: string;
  alert_name?: string;
  service_name?: string;
  severity?: string;
  environment?: string;
  description?: string;
  raw_payload?: Record<string, any>;
  [key: string]: any;
}

export interface AlertIngestResponse {
  action: "CREATED" | "CORRELATED" | "SUPPRESSED" | "REJECTED" | string;
  incident_id: string;
  alert_id: string;
  fingerprint: string;
  is_new_incident: boolean;
  service_name: string;
  severity: string;
  environment: string;
  summary: string;
}

export interface IncidentTimelineEventItem {
  id: string;
  incident_id: string;
  timestamp: string;
  event_type: string;
  service_name: string;
  title: string;
  description: string;
  severity: string;
  actor: string;
  actor_type: string;
  data_source: string;
  raw_data?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentAssignmentItem {
  id: string;
  assigned_to_id: string;
  assigned_to_name: string;
  team_name: string;
  assigned_by: string;
  role: string;
  reason?: string | null;
  created_at?: string | null;
}

export interface IncidentOwnershipSummary {
  incident_id: string;
  owner_id?: string | null;
  owner_name: string;
  assigned_team: string;
  oncall_responder: string;
  is_acknowledged: boolean;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  time_since_detection_seconds: number;
  time_since_acknowledgement_seconds?: number | null;
  is_escalated: boolean;
  escalation_status: string;
  escalation_deadline?: string | null;
  assignment_history: IncidentAssignmentItem[];
}

// Phase 10: Advanced Multi-Agent Investigation Types

export interface RankedHypothesisItem {
  id: string;
  culprit_service: string;
  hypothesis_text: string;
  confidence_score: number;
  confidence_tier: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  causal_explanation: string;
  temporal_correlation: string;
  missing_evidence_gaps: string[];
  is_confirmed: boolean;
}

export interface InvestigationReport {
  incident_id: string;
  investigation_id: string;
  total_duration_ms: number;
  completed_agents: string[];
  failed_agents: string[];
  affected_service: string;
  environment: string;
  primary_root_cause: string;
  confidence_score: number;
  confidence_tier: string;
  consensus_status: string;
  remediation_recommendations: any[];
  ranked_hypotheses: RankedHypothesisItem[];
  generated_at: string;
}

export interface AgentMessageItem {
  id: string;
  incident_id: string;
  investigation_id: string;
  sender_agent: string;
  recipient_agent: string;
  message_type: string;
  round_number: number;
  summary: string;
  created_at?: string | null;
}

export interface InvestigationGraphNode {
  id: string;
  label: string;
  type: string;
  status: string;
}

export interface InvestigationGraphEdge {
  source: string;
  target: string;
}

export interface InvestigationGraphData {
  incident_id: string;
  nodes: InvestigationGraphNode[];
  edges: InvestigationGraphEdge[];
}

// ============================================================================
// Phase 11 Root Cause Intelligence Models
// ============================================================================

export interface Phase11HypothesisItem {
  id: string;
  incident_id: string;
  investigation_id?: string | null;
  title: string;
  description: string;
  affected_service: string;
  triggering_event?: string | null;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  missing_evidence: string[];
  assumptions: string[];
  source_domains: string[];
  confidence_score: number;
  confidence_category: "VERY_HIGH" | "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT_EVIDENCE";
  status: "PROPOSED" | "INVESTIGATING" | "SUPPORTED" | "CONTRADICTED" | "REJECTED" | "INCONCLUSIVE" | "CONFIRMED";
  score_breakdown?: Record<string, any> | null;
  causal_chain_summary?: string | null;
  created_at: string;
}

export interface CompetingHypothesisAnalysis {
  incident_id: string;
  investigation_id?: string | null;
  total_hypotheses: number;
  ranked_hypotheses: Phase11HypothesisItem[];
  shared_evidence_matrix: Record<string, string[]>;
  discriminating_evidence: Record<string, string[]>;
  conflicting_evidence_notes: string[];
  unsupported_assumptions: Record<string, string[]>;
  ranking_rationale: string;
  top_hypothesis_id?: string | null;
}

export interface CounterEvidenceReport {
  hypothesis_id: string;
  hypothesis_title: string;
  disproof_attempted: boolean;
  counter_evidence_found: string[];
  missing_expected_evidence: string[];
  verdict: "SURVIVED_DISPROOF" | "WEAKENED" | "REFUTED";
  score_penalty_applied: number;
  rationale: string;
}

export interface CausalNode {
  id: string;
  label: string;
  node_type: "TRIGGERING_EVENT" | "INTERMEDIATE_FAILURE" | "CONTRIBUTING_FACTOR" | "AFFECTED_SERVICE" | "CASCADING_FAILURE" | "USER_FACING_SYMPTOM" | "ROOT_CAUSE_CANDIDATE";
  service_name?: string | null;
  timestamp?: string | null;
  is_empirical_fact: boolean;
  evidence_id?: string | null;
}

export interface CausalEdge {
  source: string;
  target: string;
  relationship: string;
  relation_type: "VERIFIED_CAUSAL" | "INFERRED_CORRELATION" | "ASSUMPTION";
  confidence: number;
}

export interface CausalGraph {
  incident_id: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  triggering_event?: string | null;
  root_cause_candidate?: string | null;
  verified_causal_ratio: number;
}

export interface SimilarIncidentMatch {
  incident_id: string;
  title: string;
  severity: string;
  similarity_score: number;
  matching_service: string;
  identified_root_cause?: string | null;
  remediation_applied?: string | null;
  remediation_successful: boolean;
  detected_at: string;
}

export interface Phase11RootCauseReport {
  incident_id: string;
  investigation_id?: string | null;
  primary_root_cause: string;
  primary_hypothesis: Phase11HypothesisItem;
  competing_analysis: CompetingHypothesisAnalysis;
  counter_evidence_reports: CounterEvidenceReport[];
  causal_graph: CausalGraph;
  similar_incidents: SimilarIncidentMatch[];
  is_recurrence: boolean;
  recurrence_count: number;
  confidence_score: number;
  confidence_category: "VERY_HIGH" | "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT_EVIDENCE";
  executive_summary: string;
  generated_at: string;
}

// =============================================================================
// Phase 12: Safe Autonomous Incident Resolution Engine
// =============================================================================

export interface Phase12ActionItem {
  action_id: string;
  name: string;
  category: "KUBERNETES" | "APPLICATION" | "INFRASTRUCTURE";
  action_type: string;
  target_resource: string;
  target_service_name: string;
  environment: string;
  parameters: Record<string, any>;
  preconditions: string[];
  expected_outcome: string;
  potential_side_effects: string[];
  risk_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  timeout_seconds: number;
  is_reversible: boolean;
  rollback_action_id?: string | null;
  verification_strategy: string;
}

export interface Phase12RiskAssessment {
  plan_id: string;
  action_id: string;
  target_resource: string;
  risk_score: number;
  risk_classification: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  incident_severity: string;
  resource_criticality: string;
  affected_resource_count: number;
  availability_impact: string;
  data_integrity_risk: string;
  cluster_health_status: string;
  is_reversible: boolean;
  rollback_available: boolean;
  potential_failure_scenarios: string[];
  required_safeguards: string[];
  impact_explanation: string;
  requires_human_approval: boolean;
  requires_emergency_override: boolean;
  generated_at: string;
}

export interface Phase12ApprovalRecord {
  approval_id: string;
  plan_id: string;
  action_id: string;
  target_resource: string;
  parameters_hash: string;
  risk_assessment: Phase12RiskAssessment;
  requesting_actor: string;
  requesting_actor_type: string;
  approving_user?: string | null;
  approver_role?: string | null;
  approval_status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED" | "CANCELLED" | "AUTO_APPROVED";
  decision_reason?: string | null;
  requested_at: string;
  decided_at?: string | null;
  expires_at: string;
  is_tampered: boolean;
}

export interface PreExecutionCheckResult {
  passed: boolean;
  cluster_identity_verified: boolean;
  namespace_verified: boolean;
  resource_identity_verified: boolean;
  resource_state_healthy: boolean;
  permissions_verified: boolean;
  approval_valid: boolean;
  action_allowlisted: boolean;
  rollback_ready: boolean;
  disruption_budget_satisfied: boolean;
  plan_fresh: boolean;
  kill_switch_inactive: boolean;
  failure_reasons: string[];
  checked_at: string;
}

export interface ResourceStateSnapshot {
  captured_at: string;
  resource_name: string;
  resource_version?: string | null;
  replicas_ready?: number | null;
  replicas_desired?: number | null;
  pod_statuses?: Array<Record<string, any>>;
  config_hash?: string | null;
  cpu_percent?: number | null;
  memory_percent?: number | null;
  error_rate_percent?: number | null;
  p95_latency_ms?: number | null;
}

export interface ActionExecutionResult {
  execution_id: string;
  plan_id: string;
  action_id: string;
  target_resource: string;
  environment: string;
  status: "PLANNED" | "PRE_CHECK_FAILED" | "EXECUTING" | "EXECUTED" | "FAILED" | "CANCELLED" | "ROLLED_BACK" | "ROLLBACK_FAILED";
  pre_state_snapshot?: ResourceStateSnapshot | null;
  post_state_snapshot?: ResourceStateSnapshot | null;
  started_at: string;
  completed_at?: string | null;
  duration_ms: number;
  idempotency_key: string;
  execution_logs: string[];
  error_message?: string | null;
  was_rolled_back: boolean;
  rollback_result?: Record<string, any> | null;
}

export interface RollbackExecutionResult {
  rollback_id: string;
  original_execution_id: string;
  action_id: string;
  target_resource: string;
  environment: string;
  success: boolean;
  pre_rollback_state?: ResourceStateSnapshot | null;
  post_rollback_state?: ResourceStateSnapshot | null;
  duration_ms: number;
  rollback_logs: string[];
  error_message?: string | null;
  executed_at: string;
}

export interface RecoveryMetricComparison {
  metric_name: string;
  before_value: number;
  after_value: number;
  unit: string;
  threshold: number;
  is_healthy: boolean;
}

export interface RecoveryVerificationReport {
  verification_id: string;
  incident_id: string;
  plan_id: string;
  status: "RECOVERY_PENDING" | "RECOVERY_SUCCESSFUL" | "RECOVERY_PARTIAL" | "RECOVERY_FAILED" | "ROLLBACK_REQUIRED";
  service_name: string;
  environment: string;
  pod_readiness_ratio: number;
  error_rate_recovered: boolean;
  latency_recovered: boolean;
  crash_loop_cleared: boolean;
  metric_comparisons: RecoveryMetricComparison[];
  health_evidence: string[];
  requires_rollback: boolean;
  summary: string;
  verified_at: string;
}

export interface ResolutionPlan {
  plan_id: string;
  incident_id: string;
  investigation_id?: string | null;
  root_cause_reference: string;
  root_cause_confidence: number;
  environment: string;
  target_service_name: string;
  affected_resources: string[];
  proposed_actions: Phase12ActionItem[];
  execution_sequence: string[];
  overall_risk_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  risk_assessment: Phase12RiskAssessment;
  approval_record: Phase12ApprovalRecord;
  pre_execution_check?: PreExecutionCheckResult | null;
  execution_result?: ActionExecutionResult | null;
  rollback_result?: RollbackExecutionResult | null;
  recovery_report?: RecoveryVerificationReport | null;
  status: string;
  plan_fingerprint: string;
  created_at: string;
  updated_at: string;
}

export interface KillSwitchState {
  is_active: boolean;
  activated_at?: string | null;
  activated_by?: string | null;
  reason?: string | null;
  in_flight_actions_aborted: number;
}


// ============================================================================
// PHASE 13 — RECOVERY VERIFICATION & SELF-LEARNING
// ============================================================================

export type Phase13RecoveryStatus =
  | "RECOVERY_PENDING"
  | "RECOVERY_SUCCESSFUL"
  | "RECOVERY_PARTIAL"
  | "RECOVERY_FAILED"
  | "RECOVERY_REGRESSION";

export interface TelemetryMetricDiff {
  metric_name: string;
  unit: string;
  before_value?: number | null;
  during_value?: number | null;
  after_value?: number | null;
  delta_value?: number | null;
  percentage_change?: number | null;
  trend: "IMPROVED" | "REGRESSED" | "UNCHANGED" | "UNKNOWN";
  threshold?: number | null;
  is_healthy: boolean;
  baseline_present: boolean;
  evaluation_notes: string;
}

export interface TelemetryComparisonReport {
  comparison_id: string;
  incident_id: string;
  service_name: string;
  environment: string;
  evaluated_at: string;
  metrics: TelemetryMetricDiff[];
  overall_trend: "IMPROVED" | "REGRESSED" | "UNCHANGED" | "UNKNOWN";
  regression_detected: boolean;
  regressed_metrics: string[];
  improved_metrics: string[];
  unchanged_metrics: string[];
  baseline_incomplete: boolean;
  missing_metrics: string[];
  recovery_stability_score: number;
  summary: string;
}

export interface AdvancedRecoveryReport {
  verification_id: string;
  incident_id: string;
  service_name: string;
  environment: string;
  status: Phase13RecoveryStatus;
  verified_at: string;
  pod_readiness_verified: boolean;
  deployment_available: boolean;
  restart_frequency_cleared: boolean;
  error_rate_recovered: boolean;
  latency_normalized: boolean;
  resources_healthy: boolean;
  database_healthy: boolean;
  dependencies_healthy: boolean;
  distributed_trace_healthy: boolean;
  telemetry_comparison?: TelemetryComparisonReport | null;
  evidence_points: string[];
  failing_reasons: string[];
  requires_escalation: boolean;
  summary: string;
}

export interface StabilityCheckPoint {
  check_index: number;
  timestamp: string;
  error_rate_percent: number;
  p95_latency_ms: number;
  replicas_ready: number;
  restart_count: number;
  is_healthy: boolean;
  drift_detected: boolean;
}

export interface RecoveryStabilityReport {
  stability_id: string;
  incident_id: string;
  service_name: string;
  observation_window_seconds: number;
  check_interval_seconds: number;
  total_checks_performed: number;
  checks: StabilityCheckPoint[];
  is_stable: boolean;
  regression_detected: boolean;
  escalation_triggered: boolean;
  status: Phase13RecoveryStatus;
  stability_confidence: number;
  notes: string;
  last_checked_at: string;
}

export interface PostmortemTask {
  task_id: string;
  title: string;
  description: string;
  owner: string;
  priority: string;
  status: string;
  due_date?: string | null;
}

export interface PostmortemReport {
  postmortem_id: string;
  incident_id: string;
  title: string;
  severity: string;
  environment: string;
  affected_services: string[];
  detected_at: string;
  acknowledged_at?: string | null;
  remediated_at?: string | null;
  resolved_at?: string | null;
  incident_duration_minutes: number;
  detection_method: string;
  verified_root_cause: string;
  root_cause_is_conclusive: boolean;
  contributing_factors: string[];
  verified_facts: string[];
  ai_interpretations: string[];
  supporting_evidence: string[];
  counter_evidence: string[];
  remediation_performed: string;
  approval_details: Record<string, any>;
  rollback_occurred: boolean;
  recovery_status: string;
  recovery_summary: string;
  before_after_telemetry?: TelemetryComparisonReport | null;
  customer_impact_summary: string;
  lessons_learned: string[];
  preventive_actions: string[];
  follow_up_tasks: PostmortemTask[];
  timeline_events: Array<Record<string, any>>;
  author: string;
  generated_at: string;
  markdown_content: string;
  html_content: string;
}

export interface IncidentKnowledgeEntry {
  incident_id: string;
  title: string;
  severity: string;
  affected_services: string[];
  environment: string;
  incident_fingerprint: string;
  error_signature: string;
  root_cause_category: string;
  verified_root_cause: string;
  deployment_sha?: string | null;
  key_metrics_impacted: string[];
  effective_remediations: string[];
  failed_remediations: string[];
  recovery_status: string;
  postmortem_id?: string | null;
  is_verified_by_human: boolean;
  learning_weight: number;
  recorded_at: string;
}

export interface SimilarIncidentMatch {
  incident_id: string;
  title: string;
  severity: string;
  similarity_score: number;
  matching_features: string[];
  common_services: string[];
  verified_root_cause: string;
  recommended_remediations: string[];
  postmortem_id?: string | null;
}

export interface FailurePattern {
  pattern_id: string;
  pattern_name: string;
  frequency_count: number;
  affected_services: string[];
  common_root_cause: string;
  error_signature: string;
  mean_time_to_detect_minutes: number;
  mean_time_to_recover_minutes: number;
  recommended_systemic_fix: string;
  detected_at: string;
}

export interface LearningPolicyChange {
  version_id: string;
  created_at: string;
  source_incident_ids: string[];
  hypothesis_ranking_weights: Record<string, number>;
  agent_task_priorities: Record<string, number>;
  evidence_collection_weights: Record<string, number>;
  rationale: string;
  human_approved: boolean;
  approved_by?: string | null;
  is_active: boolean;
  previous_version_id?: string | null;
}

export interface HumanFeedback {
  feedback_id: string;
  incident_id: string;
  reviewer: string;
  reviewer_role: string;
  rating: number;
  root_cause_accurate: boolean;
  remediation_effective: boolean;
  corrected_root_cause?: string | null;
  comments: string;
  approved_learning_update: boolean;
  submitted_at: string;
}

export interface ContinuousImprovementRecommendation {
  recommendation_id: string;
  incident_id: string;
  category: "MONITORING" | "ALERTS" | "HEALTH_CHECKS" | "RESOURCE_LIMITS" | "DEPLOYMENT_SAFEGUARDS" | "DEPENDENCY_OBSERVABILITY" | "ESCALATION_POLICIES";
  title: string;
  description: string;
  supporting_evidence: string[];
  expected_benefit: string;
  priority: "P1" | "P2" | "P3";
  complexity: "LOW" | "MEDIUM" | "HIGH";
  risk: "LOW" | "MEDIUM" | "HIGH";
  suggested_owner: string;
  verification_criteria: string;
  status: "OPEN" | "ACCEPTED" | "IMPLEMENTED" | "REJECTED";
  created_at: string;
}

// ============================================================================
// PHASE 14 — REAL-TIME ON-CALL COMMUNICATION
// ============================================================================

export interface NotificationMessage {
  notification_id: string;
  incident_id: string;
  event_type: string;
  priority: string;
  severity: string;
  title: string;
  affected_service: string;
  summary: string;
  assigned_team: string;
  required_action: string;
  incident_url: string;
  timestamp: string;
  delivered_channels: string[];
  status: string;
}

export interface OnCallShift {
  shift_id: string;
  team_name: string;
  primary_responder: string;
  primary_email: string;
  secondary_responder: string;
  secondary_email: string;
  escalation_lead: string;
  timezone: string;
  shift_start: string;
  shift_end: string;
  is_active: boolean;
  override_active: boolean;
  override_notes?: string | null;
}

export interface EscalationState {
  incident_id: string;
  current_level: number;
  escalation_count: number;
  next_deadline: string;
  is_acknowledged: boolean;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  escalation_log: Array<{ timestamp: string; event: string }>;
}

export interface AcknowledgmentRecord {
  acknowledgment_id: string;
  incident_id: string;
  responder_id: string;
  responder_role: string;
  accepted: boolean;
  rejection_reason?: string | null;
  time_to_acknowledge_seconds: number;
  acknowledged_at: string;
}

export interface TeamHandoffRecord {
  handoff_id: string;
  incident_id: string;
  from_responder: string;
  to_responder: string;
  handoff_type: string;
  incident_summary: string;
  current_severity: string;
  investigation_progress: string;
  confirmed_root_cause?: string | null;
  competing_hypotheses: string[];
  completed_actions: string[];
  pending_approvals: string[];
  remediation_status: string;
  recovery_verification_status: string;
  outstanding_risks: string[];
  next_recommended_actions: string[];
  transferred_at: string;
}

export interface IncidentChatMessage {
  message_id: string;
  incident_id: string;
  sender_name: string;
  sender_type: "HUMAN" | "AI_AGENT" | "SYSTEM";
  sender_role: string;
  content: string;
  is_pinned: boolean;
  timestamp: string;
}

export interface ChannelIntegrationConfig {
  channel_name: string;
  status: "CONFIGURED" | "NOT_CONFIGURED" | "CONNECTIVITY_ERROR";
  endpoint_masked: string;
  is_enabled: boolean;
  last_tested_at?: string | null;
  last_test_success: boolean;
}

export interface CommunicationAnalytics {
  mean_time_to_acknowledge_seconds: number;
  mean_time_to_assign_seconds: number;
  total_notifications_sent: number;
  delivery_success_rate: number;
  unacknowledged_incidents_count: number;
  handoffs_completed_count: number;
  active_responders_count: number;
}

// ============================================================================
// PHASE 15 — ADVANCED SRE INTELLIGENCE
// ============================================================================

export interface AnomalySignal {
  metric_name: string;
  current_value: number;
  baseline_mean: number;
  baseline_std: number;
  z_score: number;
  classification: "NORMAL" | "UNUSUAL" | "CONFIRMED_ANOMALY" | "INSUFFICIENT_DATA";
  unit: string;
  timestamp: string;
}

export interface MultiSignalAnomalyReport {
  report_id: string;
  service_name: string;
  overall_classification: "NORMAL" | "UNUSUAL" | "CONFIRMED_ANOMALY" | "INSUFFICIENT_DATA";
  multivariate_anomaly_score: number;
  anomalous_signals: AnomalySignal[];
  evaluated_signals_count: number;
  summary: string;
  evaluated_at: string;
}

export interface PredictedIncidentRisk {
  prediction_id: string;
  service_name: string;
  risk_category: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  risk_type: string;
  confidence_score: number;
  predicted_lead_time_minutes: number;
  supporting_signals: string[];
  missing_evidence: string[];
  recommended_proactive_investigation: string;
  created_at: string;
}

export interface ServiceHealthOverview {
  service_name: string;
  health_status: "HEALTHY" | "DEGRADED" | "AT_RISK" | "CRITICAL" | "UNKNOWN";
  availability_percent: number;
  p95_latency_ms: number;
  error_rate_percent: number;
  cpu_saturation_percent: number;
  memory_saturation_percent: number;
  active_anomalies_count: number;
  slo_status: string;
  explanation: string;
  evaluated_at: string;
}

export interface SLOTarget {
  slo_id: string;
  service_name: string;
  slo_name: string;
  target_percent: number;
  current_percent: number;
  error_budget_total_minutes: number;
  error_budget_remaining_percent: number;
  error_budget_consumed_percent: number;
  burn_rate: number;
  burn_rate_status: "NORMAL" | "ELEVATED" | "CRITICAL_BURN";
  measurement_window: string;
  is_breached: boolean;
}

export interface DeploymentRiskAssessment {
  deployment_id: string;
  service_name: string;
  git_sha: string;
  deployed_at: string;
  risk_score: number;
  risk_category: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  is_correlated_with_degradation: boolean;
  telemetry_changes: string[];
  explanation: string;
  suggested_verification: string;
}

export interface CascadingFailureRisk {
  root_service: string;
  downstream_impacted_services: string[];
  bottleneck_service: string;
  blast_radius_score: number;
  potential_impact: string;
  mitigation_recommendation: string;
}

export interface PredictiveRecommendation {
  recommendation_id: string;
  service_name: string;
  priority: string;
  risk: string;
  suggested_action: string;
  expected_outcome: string;
  verification_method: string;
  created_at: string;
}

export interface ModelEvaluationMetrics {
  model_version: string;
  anomaly_precision: number;
  false_positive_rate: number;
  prediction_accuracy: number;
  mean_lead_time_minutes: number;
  data_coverage_percent: number;
  evaluation_period: string;
}

// ============================================================================
// PHASE 16 — HACKATHON DEMONSTRATION & ORCHESTRATION
// ============================================================================

export interface DemonstrationScenario {
  scenario_id: "SCENARIO_A" | "SCENARIO_B" | "SCENARIO_C";
  title: string;
  target_service: string;
  severity: string;
  environment: string;
  fault_type: string;
  description: string;
  expected_root_cause: string;
  proposed_remediation: string;
  is_active: boolean;
}

export interface OrchestrationStep {
  step_number: number;
  name: string;
  phase_ref: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED";
  details: string;
  evidence: string[];
  started_at?: string | null;
  completed_at?: string | null;
}

export interface OrchestrationExecutionResult {
  execution_id: string;
  scenario_id: "SCENARIO_A" | "SCENARIO_B" | "SCENARIO_C";
  incident_id: string;
  title: string;
  severity: string;
  target_service: string;
  environment: string;
  total_duration_seconds: number;
  steps: OrchestrationStep[];
  root_cause_ruling: string;
  confidence_score: number;
  remediation_executed: string;
  human_approved: boolean;
  approver_role: string;
  recovery_status: string;
  postmortem_id?: string | null;
  policy_version: string;
  is_completed: boolean;
  started_at: string;
  completed_at?: string | null;
}
