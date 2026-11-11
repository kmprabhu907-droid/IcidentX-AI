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
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
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

  // Incidents
  listIncidents: (page = 1, pageSize = 20, status?: string, severity?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.set("status", status);
    if (severity) params.set("severity", severity);
    return request<PaginatedResponse<Incident>>(`/incidents?${params.toString()}`);
  },
  getIncident: (id: string) => request<Incident>(`/incidents/${id}`),
  createIncident: (payload: { title: string; summary?: string; severity: string; status?: string; impact_scope?: string }) =>
    request<Incident>("/incidents", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

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
};
