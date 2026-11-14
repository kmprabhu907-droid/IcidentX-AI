import {
  Incident,
  Service,
  ServiceDependency,
  Evidence,
  RootCauseHypothesis,
  AgentExecution,
  AuditLog,
  PaginatedResponse,
  SystemHealth,
  ClusterOverview,
  Trace,
  LogRecord,
  AnomalyAlert,
  ChaosScenario,
  SimulationStatus,
  TimelineEvent,
  CourtroomView,
  InvestigationPlanView,
  InvestigationStatus,
  TimelineView,
  RemediationAction,
  RemediationPolicy,
  ActionRegistryItem,
  VerificationReport,
  RemediationRecommendationsResponse,
  AnomalyRecordItem,
  MetricBaselineItem,
  DetectionStatus,
  RegressionRecordItem,
  FourStateComparisonData,
  RemediationEffectivenessOverview,
  EnvironmentMode,
  EnvironmentMetadata,
  EnvironmentHealth,
  InfrastructureWorkload,
  InfrastructureServiceItem,
  InfrastructureEvent,
  ResourceMetric,
  EnvironmentSwitchResponse,
  KubernetesNode,
  KubernetesNamespace,
  KubernetesPod,
  KubernetesDeployment,
  KubernetesService,
  KubernetesResourceMetrics,
  KubernetesClusterOverview,
  KubernetesConnectionDetails,
  PrometheusHealthStatus,
  PrometheusQueryResult,
  PromQLTemplate,
  OpenTelemetryTrace,
  GrafanaDashboardInfo,
  GrafanaAnnotation,
  UnifiedTelemetryTimelineItem,
  TelemetryAnomalyRecord,
  ObservabilityStackStatus,
  ProviderHealth,
  ProviderInfo,
  ModelAttribution,
  AIReasoningEvidenceItem,
  CourtroomHypothesis,
  CourtroomVerdict,
  AIIncidentReasoningReport,
  AIUsageRecord,
  AIUsageSummary,
  CircuitBreakerStatus,
  PageAlert,
  OnCallShiftStatus,
  IncidentStatistics,
  AlertRecord,
  AlertIngestPayload,
  AlertIngestResponse,
  IncidentTimelineEventItem,
  IncidentOwnershipSummary,
  InvestigationReport,
  AgentMessageItem,
  InvestigationGraphData,
  Phase11RootCauseReport,
  CompetingHypothesisAnalysis,
  CounterEvidenceReport,
  CausalGraph,
  SimilarIncidentMatch,
  ResolutionPlan,
  RecoveryVerificationReport,
  RollbackExecutionResult,
  KillSwitchState,
  AdvancedRecoveryReport,
  TelemetryComparisonReport,
  RecoveryStabilityReport,
  PostmortemReport,
  FailurePattern,
  LearningPolicyChange,
  HumanFeedback,
  ContinuousImprovementRecommendation,
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(public status: number, message: string, public details?: any) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = typeof window !== "undefined" ? localStorage.getItem("incidentx_access_token") : null;
  const orgId = typeof window !== "undefined" ? localStorage.getItem("incidentx_org_id") : null;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(orgId ? { "X-Organization-ID": orgId } : {}),
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}: ${res.statusText}`;
      let details;
      try {
        const errorJson = await res.json();
        if (errorJson.error?.message) {
          errorMsg = errorJson.error.message;
        } else if (errorJson.detail) {
          errorMsg = errorJson.detail;
        }
        details = errorJson.error?.details || errorJson.detail;
      } catch (_) {}
      throw new ApiError(res.status, errorMsg, details);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err.message || "Network request failed. Ensure backend is running on port 8000.");
  }
}

export const api = {
  // System Health
  getHealth: () => request<SystemHealth>("/health"),

  // Observability & Telemetry Core
  getClusterOverview: () => request<ClusterOverview>("/observability/overview"),
  listAlerts: (limit = 50) => request<AnomalyAlert[]>(`/observability/alerts?limit=${limit}`),
  listLiveServices: () => request<{ services: Record<string, any>; data_source: string }>("/observability/services"),
  getServiceMetrics: (serviceName: string, seconds = 60) =>
    request<{ service_name: string; seconds: number; data_source: string; history: any[] }>(
      `/observability/services/${serviceName}/metrics?seconds=${seconds}`
    ),

  // Distributed Traces
  listTraces: (params?: { limit?: number; service?: string; only_errors?: boolean; min_duration_ms?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.service) query.set("service", params.service);
    if (params?.only_errors) query.set("only_errors", "true");
    if (params?.min_duration_ms) query.set("min_duration_ms", String(params.min_duration_ms));
    return request<{ total: number; data_source: string; traces: Trace[] }>(`/telemetry/traces?${query.toString()}`);
  },
  getTrace: (traceId: string) => request<Trace>(`/telemetry/traces/${traceId}`),

  // Correlated Logs
  listLogs: (params?: { limit?: number; service?: string; level?: string; trace_id?: string; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.service) query.set("service", params.service);
    if (params?.level) query.set("level", params.level);
    if (params?.trace_id) query.set("trace_id", params.trace_id);
    if (params?.search) query.set("search", params.search);
    return request<{ total: number; data_source: string; logs: LogRecord[] }>(`/telemetry/logs?${query.toString()}`);
  },

  // Failure Injection Lab (Chaos Simulation)
  listChaosScenarios: () => request<ChaosScenario[]>("/simulation/scenarios"),
  getSimulationStatus: () => request<SimulationStatus>("/simulation/status"),
  injectChaos: (scenarioId: string, targetService?: string, durationSeconds?: number, parameters?: Record<string, any>) =>
    request<{ status: string; message: string; fault: any }>("/simulation/inject", {
      method: "POST",
      body: JSON.stringify({
        scenario_id: scenarioId,
        target_service: targetService,
        duration_seconds: durationSeconds,
        parameters: parameters || {},
      }),
    }),
  stopChaos: (scenarioId: string) =>
    request<{ status: string; message: string }>("/simulation/stop", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId }),
    }),
  stopAllChaos: () =>
    request<{ status: string; stopped_count: number; message: string }>("/simulation/stop-all", {
      method: "POST",
    }),

  // Incidents & Phase 9 Command Center
  listIncidents: (
    page = 1,
    pageSize = 20,
    status?: string,
    severity?: string,
    environment?: string,
    ownerId?: string,
    priority?: string,
    search?: string
  ) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.set("status", status);
    if (severity) params.set("severity", severity);
    if (environment) params.set("environment", environment);
    if (ownerId) params.set("owner_id", ownerId);
    if (priority) params.set("priority", priority);
    if (search) params.set("search", search);
    return request<PaginatedResponse<Incident>>(`/incidents?${params.toString()}`);
  },
  getIncident: (id: string) => request<Incident>(`/incidents/${id}`),
  createIncident: (payload: {
    title: string;
    summary?: string;
    severity: string;
    status?: string;
    priority?: string;
    environment?: string;
    source?: string;
    impact_scope?: string;
    owner_id?: string;
    owner_name?: string;
    assigned_team?: string;
  }) =>
    request<Incident>("/incidents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getIncidentStatistics: () => request<IncidentStatistics>("/incidents/statistics/summary"),
  transitionIncident: (
    incidentId: string,
    targetState: string,
    actor = "sre-operator",
    actorType = "HUMAN",
    reason?: string
  ) =>
    request<Incident>(`/incidents/${encodeURIComponent(incidentId)}/transition`, {
      method: "POST",
      body: JSON.stringify({ target_state: targetState, actor, actor_type: actorType, reason }),
    }),
  getIncidentTimelineEvents: (
    incidentId: string,
    limit = 100,
    offset = 0,
    eventType?: string
  ) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (eventType) params.set("event_type", eventType);
    return request<IncidentTimelineEventItem[]>(
      `/incidents/${encodeURIComponent(incidentId)}/timeline?${params.toString()}`
    );
  },
  assignIncidentOwner: (
    incidentId: string,
    assignedToId: string,
    assignedToName: string,
    teamName = "Platform SRE",
    assignedBy = "sre-lead@enterprise.io",
    role = "PRIMARY_RESPONDER",
    reason?: string
  ) =>
    request<Incident>(`/incidents/${encodeURIComponent(incidentId)}/assign`, {
      method: "POST",
      body: JSON.stringify({
        assigned_to_id: assignedToId,
        assigned_to_name: assignedToName,
        team_name: teamName,
        assigned_by: assignedBy,
        role,
        reason,
      }),
    }),
  reassignIncidentOwner: (
    incidentId: string,
    newOwnerId: string,
    newOwnerName: string,
    newTeamName = "Platform SRE",
    assignedBy = "sre-lead@enterprise.io",
    reason = "Shift rotation / handoff"
  ) =>
    request<Incident>(`/incidents/${encodeURIComponent(incidentId)}/reassign`, {
      method: "POST",
      body: JSON.stringify({
        new_owner_id: newOwnerId,
        new_owner_name: newOwnerName,
        new_team_name: newTeamName,
        assigned_by: assignedBy,
        reason,
      }),
    }),
  acknowledgeIncident: (
    incidentId: string,
    responderId = "sre-user-1",
    responderName = "Primary On-Call SRE"
  ) =>
    request<Incident>(`/incidents/${encodeURIComponent(incidentId)}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ responder_id: responderId, responder_name: responderName }),
    }),
  escalateIncident: (
    incidentId: string,
    reason: string,
    targetTier = "ESCALATED_TIER_2",
    escalatedBy = "oncall-operator"
  ) =>
    request<Incident>(`/incidents/${encodeURIComponent(incidentId)}/escalate`, {
      method: "POST",
      body: JSON.stringify({ reason, target_tier: targetTier, escalated_by: escalatedBy }),
    }),
  getIncidentOwnershipSummary: (incidentId: string) =>
    request<IncidentOwnershipSummary>(`/incidents/${encodeURIComponent(incidentId)}/ownership`),

  // Module 9.3: Intelligent Alert Ingestion API
  ingestAlert: (payload: AlertIngestPayload, sourceOverride?: string) => {
    const query = sourceOverride ? `?source=${encodeURIComponent(sourceOverride)}` : "";
    return request<AlertIngestResponse>(`/alerts/ingest${query}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listIngestedAlerts: (
    page = 1,
    pageSize = 20,
    serviceName?: string,
    severity?: string,
    source?: string,
    status?: string,
    incidentId?: string
  ) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (serviceName) params.set("service_name", serviceName);
    if (severity) params.set("severity", severity);
    if (source) params.set("source", source);
    if (status) params.set("status", status);
    if (incidentId) params.set("incident_id", incidentId);
    return request<PaginatedResponse<AlertRecord>>(`/alerts?${params.toString()}`);
  },
  getIngestedAlert: (alertId: string) => request<AlertRecord>(`/alerts/${encodeURIComponent(alertId)}`),

  // Services
  listServices: (page = 1, pageSize = 50) =>
    request<PaginatedResponse<Service>>(`/services?page=${page}&page_size=${pageSize}`),
  getService: (id: string) => request<Service>(`/services/${id}`),
  createService: (payload: { name: string; tier: string; service_type: string; language?: string; health_status?: string }) =>
    request<Service>("/services", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Dependencies
  listDependencies: () => request<PaginatedResponse<ServiceDependency>>("/dependencies"),

  // Investigation & Courtroom
  triggerInvestigation: (incidentId: string) =>
    request<{ status: string; message: string; investigation: any }>(
      `/incidents/${incidentId}/investigate`,
      { method: "POST" }
    ),
  getInvestigationStatus: (incidentId: string) =>
    request<InvestigationStatus>(`/incidents/${incidentId}/investigation/status`),
  getCourtroom: (incidentId: string) =>
    request<CourtroomView>(`/incidents/${incidentId}/courtroom`),
  getTimeline: (incidentId: string) =>
    request<TimelineView>(`/incidents/${incidentId}/timeline`),
  getPlanner: (incidentId: string) =>
    request<InvestigationPlanView>(`/incidents/${incidentId}/planner`),
  getIncidentEvidence: (incidentId: string) =>
    request<PaginatedResponse<Evidence>>(`/incidents/${incidentId}/evidence`),
  getIncidentHypotheses: (incidentId: string) =>
    request<PaginatedResponse<RootCauseHypothesis>>(`/incidents/${incidentId}/hypotheses`),
  getIncidentAgentExecutions: (incidentId: string) =>
    request<PaginatedResponse<AgentExecution>>(`/incidents/${incidentId}/agent-executions`),
  cancelInvestigation: (incidentId: string) =>
    request<{ incident_id: string; cancelled: boolean }>(
      `/incidents/${encodeURIComponent(incidentId)}/investigate/cancel`,
      { method: "POST" }
    ),
  getInvestigationReport: (incidentId: string) =>
    request<InvestigationReport>(`/incidents/${encodeURIComponent(incidentId)}/investigation/report`),
  getInvestigationMessages: (incidentId: string) =>
    request<AgentMessageItem[]>(`/incidents/${encodeURIComponent(incidentId)}/investigation/messages`),
  getInvestigationGraph: (incidentId: string) =>
    request<InvestigationGraphData>(`/incidents/${encodeURIComponent(incidentId)}/investigation/graph`),

  // Phase 11: Autonomous Root Cause Intelligence Engine
  evaluateRootCause: (incidentId: string, affectedService?: string) =>
    request<Phase11RootCauseReport>(
      `/incidents/${encodeURIComponent(incidentId)}/root-cause/evaluate${affectedService ? `?affected_service=${encodeURIComponent(affectedService)}` : ""}`,
      { method: "POST" }
    ),
  getRootCauseReport: (incidentId: string) =>
    request<Phase11RootCauseReport>(`/incidents/${encodeURIComponent(incidentId)}/root-cause/report`),
  getCompetingHypotheses: (incidentId: string) =>
    request<CompetingHypothesisAnalysis>(`/incidents/${encodeURIComponent(incidentId)}/root-cause/hypotheses`),
  getCounterEvidence: (incidentId: string) =>
    request<CounterEvidenceReport[]>(`/incidents/${encodeURIComponent(incidentId)}/root-cause/counter-evidence`),
  getCausalGraph: (incidentId: string) =>
    request<CausalGraph>(`/incidents/${encodeURIComponent(incidentId)}/root-cause/causal-graph`),
  getSimilarIncidents: (incidentId: string, limit: number = 5) =>
    request<SimilarIncidentMatch[]>(`/incidents/${encodeURIComponent(incidentId)}/root-cause/similar-incidents?limit=${limit}`),

  // Phase 12: Safe Autonomous Incident Resolution Engine
  generateResolutionPlan: (incidentId: string, environment?: string, targetService?: string) => {
    const params = new URLSearchParams();
    if (environment) params.append("environment", environment);
    if (targetService) params.append("target_service", targetService);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<ResolutionPlan>(`/incidents/${encodeURIComponent(incidentId)}/resolution/plan${qs}`, {
      method: "POST",
    });
  },
  getResolutionPlan: (incidentId: string) =>
    request<ResolutionPlan>(`/incidents/${encodeURIComponent(incidentId)}/resolution/plan`),
  approveResolutionPlan: (
    incidentId: string,
    payload: {
      decision: "APPROVED" | "REJECTED";
      approving_user?: string;
      user_role?: string;
      reason?: string;
      emergency_override?: boolean;
    }
  ) =>
    request<ResolutionPlan>(`/incidents/${encodeURIComponent(incidentId)}/resolution/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  executeResolutionPlan: (incidentId: string, autoRollback: boolean = true) =>
    request<ResolutionPlan>(
      `/incidents/${encodeURIComponent(incidentId)}/resolution/execute?auto_rollback=${autoRollback}`,
      { method: "POST" }
    ),
  getRecoveryVerification: (incidentId: string) =>
    request<RecoveryVerificationReport | null>(`/incidents/${encodeURIComponent(incidentId)}/resolution/verification`),
  getRollbackResult: (incidentId: string) =>
    request<RollbackExecutionResult | null>(`/incidents/${encodeURIComponent(incidentId)}/resolution/rollback`),
  getKillSwitchStatus: () =>
    request<KillSwitchState>("/resolution/kill-switch"),
  toggleKillSwitch: (payload: { is_active: boolean; user?: string; reason?: string }) =>
    request<KillSwitchState>("/resolution/kill-switch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Phase 4: Safe Autonomous Remediation & Self-Healing
  getRemediationRegistry: () =>
    request<ActionRegistryItem[]>("/remediation/registry"),
  getRemediationPolicy: () =>
    request<RemediationPolicy>("/remediation/policy"),
  updateRemediationPolicy: (payload: { mode?: string; is_autonomous_enabled?: boolean; allowlisted_action_ids?: string[]; max_actions_per_incident?: number }) =>
    request<RemediationPolicy>("/remediation/policy", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  triggerEmergencyStop: (reason?: string, requestedBy?: string) =>
    request<RemediationPolicy>("/remediation/emergency-stop", {
      method: "POST",
      body: JSON.stringify({
        reason: reason || "Manual operator emergency stop",
        requested_by: requestedBy || "operator",
      }),
    }),
  resetCircuitBreaker: () =>
    request<RemediationPolicy>("/remediation/reset-circuit-breaker", {
      method: "POST",
    }),
  getIncidentRemediationRecommendations: (incidentId: string) =>
    request<RemediationRecommendationsResponse>(
      `/incidents/${incidentId}/remediation/recommendations`
    ),
  triggerRemediationRecommendations: (incidentId: string) =>
    request<{ incident_id: string; generated_count: number; actions: RemediationAction[] }>(
      `/incidents/${incidentId}/remediation/recommend`,
      { method: "POST" }
    ),
  listIncidentRemediationActions: (incidentId: string) =>
    request<RemediationAction[]>(`/incidents/${incidentId}/remediation/actions`),
  approveRemediationAction: (incidentId: string, actionId: string, payload: { approved_by: string; comment?: string }) =>
    request<RemediationAction>(
      `/incidents/${incidentId}/remediation/actions/${actionId}/approve`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),
  rejectRemediationAction: (incidentId: string, actionId: string, payload: { rejected_by: string; reason: string }) =>
    request<RemediationAction>(
      `/incidents/${incidentId}/remediation/actions/${actionId}/reject`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),
  executeRemediationAction: (incidentId: string, actionId: string, isAutonomous = false) =>
    request<RemediationAction>(
      `/incidents/${incidentId}/remediation/actions/${actionId}/execute?is_autonomous=${isAutonomous}`,
      { method: "POST" }
    ),
  rollbackRemediationAction: (incidentId: string, actionId: string, operator = "operator") =>
    request<RemediationAction>(
      `/incidents/${incidentId}/remediation/actions/${actionId}/rollback?operator=${operator}`,
      { method: "POST" }
    ),
  getActionVerificationReport: (incidentId: string, actionId: string) =>
    request<{
      action_id: string;
      action_name: string;
      target_service: string;
      execution_status: string;
      verification_status: string;
      verification_report: VerificationReport;
      raw_verification_details: any;
    }>(`/incidents/${incidentId}/remediation/actions/${actionId}/verification`),

  // Audit Logs
  listAuditLogs: (page = 1, pageSize = 50) =>
    request<PaginatedResponse<AuditLog>>(`/audit-logs?page=${page}&page_size=${pageSize}`),

  // Stage 5.2 Anomaly & Resource-Creep Detection APIs
  listAnomalies: (params?: {
    service_name?: string;
    metric_name?: string;
    severity?: string;
    status?: string;
    start_time?: string;
    end_time?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.service_name) query.set("service_name", params.service_name);
    if (params?.metric_name) query.set("metric_name", params.metric_name);
    if (params?.severity) query.set("severity", params.severity);
    if (params?.status) query.set("status", params.status);
    if (params?.start_time) query.set("start_time", params.start_time);
    if (params?.end_time) query.set("end_time", params.end_time);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    return request<{ total: number; page: number; page_size: number; total_pages: number; items: AnomalyRecordItem[] }>(
      `/observability/anomalies?${query.toString()}`
    );
  },

  getActiveAnomalies: () =>
    request<AnomalyRecordItem[]>("/observability/anomalies/active"),

  getAnomalyDetails: (anomalyId: string) =>
    request<AnomalyRecordItem>(`/observability/anomalies/${anomalyId}`),

  updateAnomalyStatus: (anomalyId: string, status: string) =>
    request<AnomalyRecordItem>(`/observability/anomalies/${anomalyId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getDetectionStatus: () =>
    request<DetectionStatus>("/observability/detection/status"),

  triggerDetectionCycle: () =>
    request<{ status: string; candidates_detected_count: number; candidates: any[] }>(
      "/observability/detection/trigger",
      { method: "POST" }
    ),

  getServiceBaselines: (serviceIdentifier: string) =>
    request<{ service_name: string; service_id: string; baselines: Record<string, MetricBaselineItem> }>(
      `/observability/baselines/${serviceIdentifier}`
    ),

  // Stage 5.3 Regression Detection & Historical Failure Intelligence APIs
  listRegressions: (params?: {
    service_name?: string;
    metric_name?: string;
    severity?: string;
    status?: string;
    classification?: string;
    start_time?: string;
    end_time?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.service_name) query.set("service_name", params.service_name);
    if (params?.metric_name) query.set("metric_name", params.metric_name);
    if (params?.severity) query.set("severity", params.severity);
    if (params?.status) query.set("status", params.status);
    if (params?.classification) query.set("classification", params.classification);
    if (params?.start_time) query.set("start_time", params.start_time);
    if (params?.end_time) query.set("end_time", params.end_time);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());
    return request<{ total: number; page: number; page_size: number; total_pages: number; items: RegressionRecordItem[] }>(
      `/observability/regressions?${query.toString()}`
    );
  },

  getActiveRegressions: () =>
    request<RegressionRecordItem[]>("/observability/regressions/active"),

  getRegressionDetails: (regressionId: string) =>
    request<RegressionRecordItem>(`/observability/regressions/${regressionId}`),

  updateRegressionStatus: (regressionId: string, status: string) =>
    request<RegressionRecordItem>(`/observability/regressions/${regressionId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getRegressionComparison: (regressionId: string) =>
    request<FourStateComparisonData>(`/observability/regressions/${regressionId}/comparison`),

  getRegressionHistory: (regressionId: string) =>
    request<{
      regression_id: string;
      service_name: string;
      metric_name: string;
      original_incident?: any;
      previous_remediations: any[];
      first_observed_at?: string;
      last_observed_at?: string;
      lifecycle_status: string;
    }>(`/observability/regressions/${regressionId}/history`),

  getRemediationEffectiveness: () =>
    request<RemediationEffectivenessOverview>("/observability/remediation-effectiveness"),

  triggerRegressionDetection: () =>
    request<{ status: string; evaluated_records_count: number; records: RegressionRecordItem[] }>(
      "/observability/regressions/trigger",
      { method: "POST" }
    ),

  // Auth & RBAC (Stage 6.2)
  login: async (payload: { email: string; password: string }) => {
    const res = await request<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (typeof window !== "undefined" && res.access_token) {
      localStorage.setItem("incidentx_access_token", res.access_token);
      localStorage.setItem("incidentx_refresh_token", res.refresh_token);
      localStorage.setItem("incidentx_user", JSON.stringify(res.user));
    }
    return res;
  },

  register: async (payload: { email: string; password: string; full_name: string; role?: string; organization_id?: string }) => {
    return request<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  logout: async () => {
    const refreshToken = typeof window !== "undefined" ? localStorage.getItem("incidentx_refresh_token") : null;
    if (refreshToken) {
      try {
        await request<any>("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch (_) {}
    }
    if (typeof window !== "undefined") {
      localStorage.removeItem("incidentx_access_token");
      localStorage.removeItem("incidentx_refresh_token");
      localStorage.removeItem("incidentx_user");
    }
  },

  getMe: () => request<any>("/auth/me"),
  getRoles: () => request<any>("/auth/roles"),

  // Multi-Tenant Organizations (Stage 6.3)
  listOrganizations: () => request<any[]>("/organizations"),
  getOrganization: (orgId: string) => request<any>(`/organizations/${orgId}`),
  createOrganization: (payload: { name: string; slug: string; tier?: string; settings_json?: string }) =>
    request<any>("/organizations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  addOrganizationMember: (orgId: string, payload: { email: string; role: string }) =>
    request<any>(`/organizations/${orgId}/members`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listOrganizationMembers: (orgId: string) =>
    request<any[]>(`/organizations/${orgId}/members`),
  switchOrganization: async (orgId: string) => {
    const res = await request<any>("/organizations/switch", {
      method: "POST",
      body: JSON.stringify({ organization_id: orgId }),
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("incidentx_org_id", orgId);
    }
    return res;
  },

  // Phase 7 Showcase Endpoints
  getShowcaseScenarios: () =>
    request<any[]>("/showcase/scenarios"),

  launchShowcase: (scenarioId: string, autoApprove: boolean = true) =>
    request<any>("/showcase/launch", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId, auto_approve_if_required: autoApprove }),
    }),

  getShowcaseMultiAgentPipeline: (service?: string) => {
    const q = service ? `?service=${service}` : "";
    return request<any>(`/showcase/multi-agent-pipeline${q}`);
  },

  getShowcaseScorecard: () =>
    request<any>("/showcase/scorecard"),

  runRootCauseAccuracyBenchmark: () =>
    request<any>("/showcase/benchmark-accuracy", { method: "POST" }),

  // Phase 8.1 Dual-Environment Abstraction Endpoints
  getEnvironments: () =>
    request<EnvironmentMetadata[]>("/environments"),

  getActiveEnvironment: () =>
    request<EnvironmentMetadata>("/environments/active"),

  selectEnvironment: (mode: EnvironmentMode) =>
    request<EnvironmentSwitchResponse>("/environments/select", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  getEnvironmentHealth: () =>
    request<EnvironmentHealth>("/environments/health"),

  getEnvironmentServices: () =>
    request<InfrastructureServiceItem[]>("/environments/services"),

  getEnvironmentWorkloads: (namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<InfrastructureWorkload[]>(`/environments/workloads${q}`);
  },

  getWorkloadStatus: (workloadId: string, namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<any>(`/environments/workloads/${encodeURIComponent(workloadId)}/status${q}`);
  },

  getEnvironmentEvents: (limit: number = 50, namespace?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (namespace) params.set("namespace", namespace);
    return request<InfrastructureEvent[]>(`/environments/events?${params.toString()}`);
  },

  getEnvironmentMetrics: (workloadId?: string) => {
    const q = workloadId ? `?workload_id=${encodeURIComponent(workloadId)}` : "";
    return request<ResourceMetric[]>(`/environments/metrics${q}`);
  },

  // Phase 8.3 Live Observability (Prometheus, OpenTelemetry, Grafana)
  getObservabilityStatus: () =>
    request<ObservabilityStackStatus>("/observability/status"),

  getPrometheusHealth: () =>
    request<PrometheusHealthStatus>("/observability/prometheus/health"),

  listAvailableMetrics: (metric?: string) => {
    const q = metric ? `?metric=${encodeURIComponent(metric)}` : "";
    return request<{ count: number; metrics: any[] }>(`/observability/metrics${q}`);
  },

  getMetricsCatalog: (category?: string) => {
    const q = category ? `?category=${encodeURIComponent(category)}` : "";
    return request<{ count: number; catalog: PromQLTemplate[] }>(`/observability/metrics/catalog${q}`);
  },

  executeInstantMetricQuery: (query: string, time?: string) => {
    const q = new URLSearchParams({ query });
    if (time) q.set("time", time);
    return request<PrometheusQueryResult>(`/observability/metrics/query?${q.toString()}`);
  },

  executeRangeMetricQuery: (query: string, start: string, end: string, step: string = "15s") => {
    const q = new URLSearchParams({ query, start, end, step });
    return request<PrometheusQueryResult>(`/observability/metrics/query_range?${q.toString()}`);
  },

  listOtelTraces: (params?: { serviceName?: string; onlyErrors?: boolean; incidentId?: string; minDurationMs?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.serviceName) q.set("service_name", params.serviceName);
    if (params?.onlyErrors) q.set("only_errors", "true");
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    if (params?.minDurationMs) q.set("min_duration_ms", String(params.minDurationMs));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ count: number; traces: OpenTelemetryTrace[] }>(`/observability/traces${qs}`);
  },

  getOtelTraceDetail: (traceId: string) =>
    request<any>(`/observability/traces/${encodeURIComponent(traceId)}`),

  ingestOtelTraces: (payload: any) =>
    request<any>("/observability/traces/ingest", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCorrelatedTimeline: (incidentId: string, limit: number = 100) =>
    request<{ incident_id: string; count: number; timeline: UnifiedTelemetryTimelineItem[] }>(
      `/observability/timeline/${encodeURIComponent(incidentId)}?limit=${limit}`
    ),

  searchGrafanaDashboards: (query: string = "") => {
    const q = query ? `?query=${encodeURIComponent(query)}` : "";
    return request<GrafanaDashboardInfo[]>(`/observability/grafana/dashboards${q}`);
  },

  getGrafanaDeepLink: (params?: { dashboardUid?: string; fromMs?: number; toMs?: number; namespace?: string; service?: string; incidentId?: string }) => {
    const q = new URLSearchParams();
    if (params?.dashboardUid) q.set("dashboard_uid", params.dashboardUid);
    if (params?.fromMs) q.set("from_time_ms", String(params.fromMs));
    if (params?.toMs) q.set("to_time_ms", String(params.toMs));
    if (params?.namespace) q.set("namespace", params.namespace);
    if (params?.service) q.set("service", params.service);
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ url: string }>(`/observability/grafana/deep-link${qs}`);
  },

  createGrafanaAnnotation: (payload: { text: string; tags?: string[]; dashboardUid?: string; timeMs?: number }) =>
    request<any>("/observability/grafana/annotations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listExplainableAnomalies: (limit: number = 50) =>
    request<{ count: number; anomalies: TelemetryAnomalyRecord[] }>(`/observability/anomalies/explainable?limit=${limit}`),

  evaluateMetricAnomaly: (payload: { resource_name: string; metric_name: string; current_value: number; data_source?: string }) =>
    request<any>("/observability/anomalies/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const reliabilityApi = {
  getOverview: () => request<any>("/observability/overview"),

  getAnomalies: (params?: { page_size?: number; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.page_size) q.set("page_size", params.page_size.toString());
    if (params?.status) q.set("status", params.status);
    return request<any>(`/observability/anomalies?${q.toString()}`);
  },

  getActiveRegressions: () =>
    request<any[]>("/observability/regressions/active"),

  getIncidentMemories: (params?: { service_name?: string; severity?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.service_name) q.set("service_name", params.service_name);
    if (params?.severity) q.set("severity", params.severity);
    if (params?.limit) q.set("limit", params.limit.toString());
    return request<any>(`/reliability/memory/incidents?${q.toString()}`);
  },

  getIncidentMemoryDetails: (incidentId: string) =>
    request<any>(`/reliability/memory/incidents/${incidentId}`),

  searchMemory: (body: any) =>
    request<any>("/reliability/memory/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getRemediationHistory: (actionId?: string) => {
    const q = actionId ? `?action_id=${actionId}` : "";
    return request<any>(`/reliability/memory/remediation-history${q}`);
  },

  getPredictions: (serviceName?: string) => {
    const q = serviceName ? `?service_name=${serviceName}` : "";
    return request<any>(`/reliability/predictions${q}`);
  },

  getForecast: (serviceId: string, metricName?: string) => {
    const q = metricName ? `?metric_name=${metricName}` : "";
    return request<any>(`/reliability/forecast/${serviceId}${q}`);
  },

  getCapacityRisks: () =>
    request<any>("/reliability/capacity-risk"),

  getSLOs: (serviceName?: string) => {
    const q = serviceName ? `?service_name=${serviceName}` : "";
    return request<any>(`/reliability/slo${q}`);
  },

  getErrorBudgets: (serviceName?: string) => {
    const q = serviceName ? `?service_name=${serviceName}` : "";
    return request<any>(`/reliability/error-budget${q}`);
  },

  getBurnRates: (serviceName?: string) => {
    const q = serviceName ? `?service_name=${serviceName}` : "";
    return request<any>(`/reliability/burn-rate${q}`);
  },

  getTimeMachine: (incidentId: string) =>
    request<any>(`/reliability/time-machine/${incidentId}`),

  getTimeMachineState: (incidentId: string, timestamp: string) =>
    request<any>(`/reliability/time-machine/${incidentId}/state-at/${encodeURIComponent(timestamp)}`),

  getCausalGraph: (incidentId: string) =>
    request<any>(`/reliability/time-machine/${incidentId}/causal-graph`),

  runAgentAssessment: (body?: { service_name?: string; incident_id?: string }) =>
    request<any>("/reliability/agent/assess", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),

  getAgentLastRun: () =>
    request<any>("/reliability/agent/last-run"),

  // Phase 7 Showcase Endpoints
  getShowcaseScenarios: () =>
    request<any[]>("/showcase/scenarios"),

  launchShowcase: (scenarioId: string, autoApprove: boolean = true) =>
    request<any>("/showcase/launch", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId, auto_approve_if_required: autoApprove }),
    }),

  getShowcaseMultiAgentPipeline: (service?: string) => {
    const q = service ? `?service=${service}` : "";
    return request<any>(`/showcase/multi-agent-pipeline${q}`);
  },

  getShowcaseScorecard: () =>
    request<any>("/showcase/scorecard"),

  runRootCauseAccuracyBenchmark: () =>
    request<any>("/showcase/benchmark-accuracy", { method: "POST" }),

  // Phase 8.1 Dual-Environment Abstraction Endpoints
  getEnvironments: () =>
    request<EnvironmentMetadata[]>("/environments"),

  getActiveEnvironment: () =>
    request<EnvironmentMetadata>("/environments/active"),

  selectEnvironment: (mode: EnvironmentMode) =>
    request<EnvironmentSwitchResponse>("/environments/select", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  getEnvironmentHealth: () =>
    request<EnvironmentHealth>("/environments/health"),

  getEnvironmentServices: () =>
    request<InfrastructureServiceItem[]>("/environments/services"),

  getEnvironmentWorkloads: (namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<InfrastructureWorkload[]>(`/environments/workloads${q}`);
  },

  getWorkloadStatus: (workloadId: string, namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<any>(`/environments/workloads/${encodeURIComponent(workloadId)}/status${q}`);
  },

  getEnvironmentEvents: (limit: number = 50, namespace?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (namespace) params.set("namespace", namespace);
    return request<InfrastructureEvent[]>(`/environments/events?${params.toString()}`);
  },

  getEnvironmentMetrics: (workloadId?: string) => {
    const q = workloadId ? `?workload_id=${encodeURIComponent(workloadId)}` : "";
    return request<ResourceMetric[]>(`/environments/metrics${q}`);
  },

  // Phase 8.3 Live Observability (Prometheus, OpenTelemetry, Grafana)
  getObservabilityStatus: () =>
    request<ObservabilityStackStatus>("/observability/status"),

  getPrometheusHealth: () =>
    request<PrometheusHealthStatus>("/observability/prometheus/health"),

  listAvailableMetrics: (metric?: string) => {
    const q = metric ? `?metric=${encodeURIComponent(metric)}` : "";
    return request<{ count: number; metrics: any[] }>(`/observability/metrics${q}`);
  },

  getMetricsCatalog: (category?: string) => {
    const q = category ? `?category=${encodeURIComponent(category)}` : "";
    return request<{ count: number; catalog: PromQLTemplate[] }>(`/observability/metrics/catalog${q}`);
  },

  executeInstantMetricQuery: (query: string, time?: string) => {
    const q = new URLSearchParams({ query });
    if (time) q.set("time", time);
    return request<PrometheusQueryResult>(`/observability/metrics/query?${q.toString()}`);
  },

  executeRangeMetricQuery: (query: string, start: string, end: string, step: string = "15s") => {
    const q = new URLSearchParams({ query, start, end, step });
    return request<PrometheusQueryResult>(`/observability/metrics/query_range?${q.toString()}`);
  },

  listOtelTraces: (params?: { serviceName?: string; onlyErrors?: boolean; incidentId?: string; minDurationMs?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.serviceName) q.set("service_name", params.serviceName);
    if (params?.onlyErrors) q.set("only_errors", "true");
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    if (params?.minDurationMs) q.set("min_duration_ms", String(params.minDurationMs));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ count: number; traces: OpenTelemetryTrace[] }>(`/observability/traces${qs}`);
  },

  getOtelTraceDetail: (traceId: string) =>
    request<any>(`/observability/traces/${encodeURIComponent(traceId)}`),

  ingestOtelTraces: (payload: any) =>
    request<any>("/observability/traces/ingest", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCorrelatedTimeline: (incidentId: string, limit: number = 100) =>
    request<{ incident_id: string; count: number; timeline: UnifiedTelemetryTimelineItem[] }>(
      `/observability/timeline/${encodeURIComponent(incidentId)}?limit=${limit}`
    ),

  searchGrafanaDashboards: (query: string = "") => {
    const q = query ? `?query=${encodeURIComponent(query)}` : "";
    return request<GrafanaDashboardInfo[]>(`/observability/grafana/dashboards${q}`);
  },

  getGrafanaDeepLink: (params?: { dashboardUid?: string; fromMs?: number; toMs?: number; namespace?: string; service?: string; incidentId?: string }) => {
    const q = new URLSearchParams();
    if (params?.dashboardUid) q.set("dashboard_uid", params.dashboardUid);
    if (params?.fromMs) q.set("from_time_ms", String(params.fromMs));
    if (params?.toMs) q.set("to_time_ms", String(params.toMs));
    if (params?.namespace) q.set("namespace", params.namespace);
    if (params?.service) q.set("service", params.service);
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ url: string }>(`/observability/grafana/deep-link${qs}`);
  },

  createGrafanaAnnotation: (payload: { text: string; tags?: string[]; dashboardUid?: string; timeMs?: number }) =>
    request<any>("/observability/grafana/annotations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listExplainableAnomalies: (limit: number = 50) =>
    request<{ count: number; anomalies: TelemetryAnomalyRecord[] }>(`/observability/anomalies/explainable?limit=${limit}`),

  evaluateMetricAnomaly: (payload: { resource_name: string; metric_name: string; current_value: number; data_source?: string }) =>
    request<any>("/observability/anomalies/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const authApi = {
  login: api.login,
  register: api.register,
  logout: api.logout,
  getMe: api.getMe,
  getRoles: api.getRoles,
};

// Phase 8.2 Kubernetes Integration Endpoints
export const kubernetesApi = {
  getConnection: () =>
    request<KubernetesConnectionDetails>("/kubernetes/connection"),

  getClusterOverview: () =>
    request<KubernetesClusterOverview>("/kubernetes/cluster"),

  getHealth: () =>
    request<EnvironmentHealth>("/kubernetes/health"),

  listNodes: () =>
    request<KubernetesNode[]>("/kubernetes/nodes"),

  listNamespaces: () =>
    request<KubernetesNamespace[]>("/kubernetes/namespaces"),

  listPods: (params?: { namespace?: string; phase?: string; search?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.namespace) q.set("namespace", params.namespace);
    if (params?.phase) q.set("phase", params.phase);
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<KubernetesPod[]>(`/kubernetes/pods${qs}`);
  },

  listDeployments: (namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<KubernetesDeployment[]>(`/kubernetes/deployments${q}`);
  },

  listServices: (namespace?: string) => {
    const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
    return request<KubernetesService[]>(`/kubernetes/services${q}`);
  },

  listEvents: (params?: { namespace?: string; onlyWarnings?: boolean; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.namespace) q.set("namespace", params.namespace);
    if (params?.onlyWarnings) q.set("only_warnings", "true");
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<InfrastructureEvent[]>(`/kubernetes/events${qs}`);
  },

  getMetrics: (workloadId?: string, namespace?: string) => {
    const q = new URLSearchParams();
    if (workloadId) q.set("workload_id", workloadId);
    if (namespace) q.set("namespace", namespace);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<KubernetesResourceMetrics[]>(`/kubernetes/metrics${qs}`);
  },
};

// Phase 8.3 Live Observability Endpoints
export const observabilityApi = {
  getObservabilityStatus: () =>
    request<ObservabilityStackStatus>("/observability/status"),

  getPrometheusHealth: () =>
    request<PrometheusHealthStatus>("/observability/prometheus/health"),

  listAvailableMetrics: (metric?: string) => {
    const q = metric ? `?metric=${encodeURIComponent(metric)}` : "";
    return request<{ count: number; metrics: any[] }>(`/observability/metrics${q}`);
  },

  getMetricsCatalog: (category?: string) => {
    const q = category ? `?category=${encodeURIComponent(category)}` : "";
    return request<{ count: number; catalog: PromQLTemplate[] }>(`/observability/metrics/catalog${q}`);
  },

  executeInstantMetricQuery: (query: string, time?: string) => {
    const q = new URLSearchParams({ query });
    if (time) q.set("time", time);
    return request<PrometheusQueryResult>(`/observability/metrics/query?${q.toString()}`);
  },

  executeRangeMetricQuery: (query: string, start: string, end: string, step: string = "15s") => {
    const q = new URLSearchParams({ query, start, end, step });
    return request<PrometheusQueryResult>(`/observability/metrics/query_range?${q.toString()}`);
  },

  listOtelTraces: (params?: { serviceName?: string; onlyErrors?: boolean; incidentId?: string; minDurationMs?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.serviceName) q.set("service_name", params.serviceName);
    if (params?.onlyErrors) q.set("only_errors", "true");
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    if (params?.minDurationMs) q.set("min_duration_ms", String(params.minDurationMs));
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ count: number; traces: OpenTelemetryTrace[] }>(`/observability/traces${qs}`);
  },

  getOtelTraceDetail: (traceId: string) =>
    request<any>(`/observability/traces/${encodeURIComponent(traceId)}`),

  ingestOtelTraces: (payload: any) =>
    request<any>("/observability/traces/ingest", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCorrelatedTimeline: (incidentId: string, limit: number = 100) =>
    request<{ incident_id: string; count: number; timeline: UnifiedTelemetryTimelineItem[] }>(
      `/observability/timeline/${encodeURIComponent(incidentId)}?limit=${limit}`
    ),

  searchGrafanaDashboards: (query: string = "") => {
    const q = query ? `?query=${encodeURIComponent(query)}` : "";
    return request<GrafanaDashboardInfo[]>(`/observability/grafana/dashboards${q}`);
  },

  getGrafanaDeepLink: (params?: { dashboardUid?: string; fromMs?: number; toMs?: number; namespace?: string; service?: string; incidentId?: string }) => {
    const q = new URLSearchParams();
    if (params?.dashboardUid) q.set("dashboard_uid", params.dashboardUid);
    if (params?.fromMs) q.set("from_time_ms", String(params.fromMs));
    if (params?.toMs) q.set("to_time_ms", String(params.toMs));
    if (params?.namespace) q.set("namespace", params.namespace);
    if (params?.service) q.set("service", params.service);
    if (params?.incidentId) q.set("incident_id", params.incidentId);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return request<{ url: string }>(`/observability/grafana/deep-link${qs}`);
  },

  createGrafanaAnnotation: (payload: { text: string; tags?: string[]; dashboardUid?: string; timeMs?: number }) =>
    request<any>("/observability/grafana/annotations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listExplainableAnomalies: (limit: number = 50) =>
    request<{ count: number; anomalies: TelemetryAnomalyRecord[] }>(`/observability/anomalies/explainable?limit=${limit}`),

  evaluateMetricAnomaly: (payload: { resource_name: string; metric_name: string; current_value: number; data_source?: string }) =>
    request<any>("/observability/anomalies/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};


export const aiApi = {
  getProviders: () =>
    request<{
      active_primary_provider: string;
      active_secondary_provider: string;
      fallback_provider: string;
      providers: ProviderInfo[];
    }>("/ai/providers"),

  getProvidersHealth: () =>
    request<{
      status: string;
      providers: Record<string, ProviderHealth>;
    }>("/ai/providers/health"),

  getModels: () =>
    request<Record<string, { id: string; name: string; tier: string }[]>>("/ai/models"),

  getConfiguration: () =>
    request<{
      primary_provider: string;
      secondary_provider: string;
      gemini_model: string;
      gemini_configured: boolean;
      openai_model: string;
      openai_configured: boolean;
      ollama_base_url: string;
      ollama_model: string;
      vllm_base_url: string;
      vllm_model: string;
      daily_token_budget: number;
      circuit_breaker_max_failures: number;
      circuit_breaker_cooldown_seconds: number;
    }>("/ai/configuration"),

  getUsage: () =>
    request<AIUsageSummary>("/ai/usage"),

  getIncidentUsage: (incidentId: string) =>
    request<{
      incident_id: string;
      request_count: number;
      total_tokens: number;
      total_estimated_cost_usd: number;
      records: AIUsageRecord[];
    }>(`/ai/usage/${encodeURIComponent(incidentId)}`),

  runReasoning: (incidentId: string, payload?: { preferred_provider?: string; preferred_model?: string }) =>
    request<AIIncidentReasoningReport>(`/ai/reasoning/${encodeURIComponent(incidentId)}/run`, {
      method: "POST",
      body: JSON.stringify(payload || {}),
    }),

  getReasoning: (incidentId: string) =>
    request<AIIncidentReasoningReport>(`/ai/reasoning/${encodeURIComponent(incidentId)}`),

  getHypotheses: (incidentId: string) =>
    request<{
      incident_id: string;
      hypotheses: CourtroomHypothesis[];
      leading_hypothesis_id: string;
      confidence_score: number;
    }>(`/ai/reasoning/${encodeURIComponent(incidentId)}/hypotheses`),

  getCourtroom: (incidentId: string) =>
    request<CourtroomVerdict>(`/ai/reasoning/${encodeURIComponent(incidentId)}/courtroom`),

  getEvidence: (incidentId: string) =>
    request<{
      incident_id: string;
      evidence_count: number;
      evidence_items: AIReasoningEvidenceItem[];
    }>(`/ai/reasoning/${encodeURIComponent(incidentId)}/evidence`),

  updateHypothesisLifecycle: (
    incidentId: string,
    payload: { hypothesis_id: string; new_status: string; reason?: string }
  ) =>
    request<{
      status: string;
      incident_id: string;
      hypothesis_id: string;
      new_status: string;
    }>(`/ai/reasoning/${encodeURIComponent(incidentId)}/hypotheses/lifecycle`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getCircuitBreakers: () =>
    request<{
      status: string;
      circuit_breakers: Record<string, CircuitBreakerStatus>;
    }>("/ai/circuit-breaker"),

  resetCircuitBreaker: (providerName?: string) => {
    const q = providerName ? `?provider_name=${encodeURIComponent(providerName)}` : "";
    return request<{ status: string; message: string }>(`/ai/circuit-breaker/reset${q}`, {
      method: "POST",
    });
  },
};

export const oncallApi = {
  getStatus: () =>
    request<{
      shift: OnCallShiftStatus;
      active_pages: PageAlert[];
      all_pages: PageAlert[];
    }>("/oncall/status"),

  ingestPage: (payload: {
    service_name: string;
    severity?: string;
    source?: string;
    summary: string;
    incident_id?: string;
  }) =>
    request<{
      status: string;
      page: PageAlert;
      message: string;
    }>("/oncall/page", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  triageIncident: (incidentId: string) =>
    request<{
      incident_id: string;
      status: string;
      incident_title: string;
      severity: string;
      impact_scope: string;
      triage_summary: string;
      confidence_score: number;
      leading_root_cause: string;
      recommended_action: any;
      evidence_count: number;
      model_attribution: any;
    }>(`/oncall/triage/${encodeURIComponent(incidentId)}`, {
      method: "POST",
    }),

  chat: (message: string, incidentId?: string) =>
    request<{
      role: string;
      content: string;
      attribution?: string;
    }>("/oncall/chat", {
      method: "POST",
      body: JSON.stringify({ message, incident_id: incidentId }),
    }),

  draftUpdate: (incidentId: string, audience: string = "SLACK") =>
    request<{
      incident_id: string;
      audience: string;
      slack_message: string;
      status: string;
      severity: string;
      timestamp: string;
    }>(`/oncall/update/${encodeURIComponent(incidentId)}/draft?audience=${encodeURIComponent(audience)}`, {
      method: "POST",
    }),

  generatePostmortem: (incidentId: string) =>
    request<{
      incident_id: string;
      title: string;
      severity: string;
      markdown_report: string;
      generated_at: string;
    }>(`/oncall/postmortem/${encodeURIComponent(incidentId)}`, {
      method: "POST",
    }),

  escalate: (pageId: string, reason: string) =>
    request<{
      status: string;
      page_id: string;
      incident_id?: string;
      service_name: string;
      escalated_to: string;
      escalation_reason: string;
      escalated_at: string;
    }>(`/oncall/escalate/${encodeURIComponent(pageId)}`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  runMidnightMeltdownScenario: () =>
    request<{
      scenario_id: string;
      scenario_title: string;
      incident_id: string;
      page_id: string;
      mtta_seconds: number;
      mttr_seconds: number;
      total_execution_ms: number;
      completed_agents: string[];
      root_cause_ruling: string;
      confidence_score: number;
      remediation_action: any;
      approval_granted: boolean;
      recovery_status: string;
      slack_announcement: string;
      postmortem_summary: string;
      lifecycle_stages: any[];
    }>("/oncall/scenarios/midnight-meltdown", {
      method: "POST",
    }),
};


// ============================================================================
// PHASE 13 — RECOVERY VERIFICATION & SELF-LEARNING API
// ============================================================================

export const learningApi = {
  verifyRecovery: (
    incidentId: string,
    payload: { service_name: string; environment?: string; custom_criteria?: any }
  ) =>
    request<AdvancedRecoveryReport>(
      `/incidents/${encodeURIComponent(incidentId)}/recovery/verify`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  getRecoveryVerification: (incidentId: string) =>
    request<AdvancedRecoveryReport>(
      `/incidents/${encodeURIComponent(incidentId)}/recovery/verification`
    ),

  getTelemetryComparison: (incidentId: string) =>
    request<TelemetryComparisonReport>(
      `/incidents/${encodeURIComponent(incidentId)}/telemetry-comparison`
    ),

  checkStability: (
    incidentId: string,
    payload: { service_name: string; observation_window_seconds?: number; simulate_regression?: boolean }
  ) =>
    request<RecoveryStabilityReport>(
      `/incidents/${encodeURIComponent(incidentId)}/stability/check`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  getStability: (incidentId: string) =>
    request<RecoveryStabilityReport>(
      `/incidents/${encodeURIComponent(incidentId)}/stability`
    ),

  generatePostmortem: (
    incidentId: string,
    payload: {
      title: string;
      severity?: string;
      environment?: string;
      affected_services: string[];
      verified_root_cause: string;
      root_cause_is_conclusive?: boolean;
      remediation_performed?: string;
      customer_impact_summary?: string;
    }
  ) =>
    request<PostmortemReport>(
      `/incidents/${encodeURIComponent(incidentId)}/postmortem`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  getPostmortem: (incidentId: string) =>
    request<PostmortemReport>(
      `/incidents/${encodeURIComponent(incidentId)}/postmortem`
    ),

  getPostmortemHtmlUrl: (incidentId: string) =>
    `${API_BASE_URL}/incidents/${encodeURIComponent(incidentId)}/postmortem/html`,

  searchKnowledge: (params?: { service?: string; error?: string; query?: string }) => {
    const q = new URLSearchParams();
    if (params?.service) q.append("service", params.service);
    if (params?.error) q.append("error", params.error);
    if (params?.query) q.append("query", params.query);
    return request<SimilarIncidentMatch[]>(`/learning/knowledge/search?${q.toString()}`);
  },

  getRecurringPatterns: () =>
    request<FailurePattern[]>("/learning/patterns"),

  getLearningPolicy: () =>
    request<{
      active_policy: LearningPolicyChange;
      history: LearningPolicyChange[];
      total_versions: number;
    }>("/learning/policy"),

  rollbackPolicy: (targetVersionId: string, rolledBackBy?: string) =>
    request<{ status: string; active_version: string; rolled_back_by: string }>(
      "/learning/policy/rollback",
      {
        method: "POST",
        body: JSON.stringify({
          target_version_id: targetVersionId,
          rolled_back_by: rolledBackBy || "oncall-lead",
        }),
      }
    ),

  submitFeedback: (
    incidentId: string,
    payload: { reviewer: string; rating: number; comments: string; corrected_root_cause?: string }
  ) =>
    request<HumanFeedback>(
      `/incidents/${encodeURIComponent(incidentId)}/feedback`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  getRecommendations: (incidentId: string) =>
    request<ContinuousImprovementRecommendation[]>(
      `/incidents/${encodeURIComponent(incidentId)}/recommendations`
    ),
};


// ============================================================================
// PHASE 14 — COMMUNICATION API
// ============================================================================

export const communicationApi = {
  sendNotification: (payload: {
    incident_id: string;
    event_type: string;
    severity?: string;
    title: string;
    affected_service: string;
    summary: string;
  }) =>
    request<any>("/communication/notifications", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listNotifications: (incidentId?: string) =>
    request<any[]>(`/communication/notifications${incidentId ? `?incident_id=${encodeURIComponent(incidentId)}` : ""}`),

  listShifts: () =>
    request<any[]>("/communication/shifts"),

  getActiveShift: (team: string = "Core SRE") =>
    request<any>(`/communication/shifts/active?team=${encodeURIComponent(team)}`),

  setShiftOverride: (shiftId: string, payload: { override_responder: string; reason: string }) =>
    request<any>(`/communication/shifts/${encodeURIComponent(shiftId)}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  acknowledge: (incidentId: string, payload: { responder_id: string; responder_role?: string; accepted?: boolean; rejection_reason?: string }) =>
    request<any>(`/communication/incidents/${encodeURIComponent(incidentId)}/acknowledge`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createHandoff: (incidentId: string, payload: any) =>
    request<any>(`/communication/incidents/${encodeURIComponent(incidentId)}/handoff`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listHandoffs: (incidentId: string) =>
    request<any[]>(`/communication/incidents/${encodeURIComponent(incidentId)}/handoffs`),

  postChat: (incidentId: string, payload: { sender_name: string; sender_type?: string; content: string; is_pinned?: boolean }) =>
    request<any>(`/communication/incidents/${encodeURIComponent(incidentId)}/chat`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getChat: (incidentId: string) =>
    request<any[]>(`/communication/incidents/${encodeURIComponent(incidentId)}/chat`),

  listIntegrations: () =>
    request<any[]>("/communication/integrations"),

  getAnalytics: () =>
    request<any>("/communication/analytics"),
};

// ============================================================================
// PHASE 15 — SRE INTELLIGENCE API
// ============================================================================

export const sreIntelligenceApi = {
  getAnomalies: (service: string = "payment-service") =>
    request<any>(`/sre-intelligence/anomalies?service=${encodeURIComponent(service)}`),

  getPredictions: (service: string = "payment-service") =>
    request<any[]>(`/sre-intelligence/predictions?service=${encodeURIComponent(service)}`),

  getHealth: (service: string = "payment-service") =>
    request<any>(`/sre-intelligence/health?service=${encodeURIComponent(service)}`),

  getSlos: (service: string = "payment-service") =>
    request<any[]>(`/sre-intelligence/slos?service=${encodeURIComponent(service)}`),

  getDeploymentCorrelation: (service: string = "payment-service") =>
    request<any>(`/sre-intelligence/deployments/correlate?service=${encodeURIComponent(service)}`),

  getCascadingRisk: (service: string = "payment-service") =>
    request<any>(`/sre-intelligence/cascading?service=${encodeURIComponent(service)}`),

  getRecommendations: (service: string = "payment-service") =>
    request<any[]>(`/sre-intelligence/recommendations?service=${encodeURIComponent(service)}`),

  getEvaluation: () =>
    request<any>("/sre-intelligence/evaluation"),
};

// ============================================================================
// PHASE 16 — HACKATHON DEMONSTRATION & ORCHESTRATION API
// ============================================================================

export const demonstrationApi = {
  listScenarios: () =>
    request<any[]>("/demonstration/scenarios"),

  executeScenario: (scenarioId: string, environment: string = "DEMOMESH") =>
    request<any>(`/demonstration/scenarios/${encodeURIComponent(scenarioId)}/execute`, {
      method: "POST",
      body: JSON.stringify({ environment }),
    }),

  resetScenarios: () =>
    request<any>("/demonstration/scenarios/reset", {
      method: "POST",
    }),

  listExecutions: () =>
    request<any[]>("/demonstration/executions"),

  getExecution: (executionId: string) =>
    request<any>(`/demonstration/executions/${encodeURIComponent(executionId)}`),
};
