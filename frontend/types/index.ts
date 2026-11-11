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
