# IncidentX AI — Phase 5 API Reference
## Continuous Reliability Intelligence Endpoints

All Phase 5 endpoints are mounted under `/api/v1` and fully documented in OpenAPI.

### 1. Observability & Regression Endpoints (`/api/v1/observability`)
- `GET /api/v1/observability/overview`: High-level cluster health, throughput, active anomaly count.
- `GET /api/v1/observability/anomalies`: Multi-attribute filtered query of persisted anomaly records.
- `GET /api/v1/observability/anomalies/active`: Real-time active alerts across all 5 detector modules.
- `GET /api/v1/observability/regressions`: Paginated post-remediation regression records.
- `GET /api/v1/observability/regressions/active`: Active confirmed/investigating regressions.
- `GET /api/v1/observability/regressions/{regression_id}/comparison`: Four-state comparative delta report.
- `POST /api/v1/observability/regressions/trigger`: Manual/scheduled regression scan trigger.

### 2. Reliability Memory Endpoints (`/api/v1/reliability/memory`)
- `GET /api/v1/reliability/memory/incidents`: List historical 20-dimension memory records.
- `GET /api/v1/reliability/memory/incidents/{incident_id}`: Detailed 20-dimension memory record.
- `POST /api/v1/reliability/memory/search`: Multi-criteria structured SQL & keyword search.
- `GET /api/v1/reliability/memory/remediation-history`: Empirical remediation effectiveness, side-effects, and advice.
- `GET /api/v1/reliability/memory/similar-incidents`: Fingerprint similarity ranking with the 6 SRE explanation answers.

### 3. Predictive Reliability Endpoints (`/api/v1/reliability`)
- `GET /api/v1/reliability/predictions`: Active metric growth rates, slopes, and Time-to-Exhaustion (TTE).
- `GET /api/v1/reliability/forecast/{service_id}`: Forward 30-minute projections with 95% confidence bounds.
- `GET /api/v1/reliability/capacity-risk`: Cluster-wide capacity hazard ranking with prescriptive recommendations.

### 4. SLO & Error Budget Endpoints (`/api/v1/reliability`)
- `GET /api/v1/reliability/slo`: Service Level Objectives, targets, and real-time SLI compliance.
- `GET /api/v1/reliability/error-budget`: Remaining error budget percentages and status tiers.
- `GET /api/v1/reliability/burn-rate`: Multi-window burn rates (1h, 6h, 24h, 3d, 14d, 30d) and fast/slow burn alerts.

### 5. Incident Time Machine Endpoints (`/api/v1/reliability/time-machine`)
- `GET /api/v1/reliability/time-machine/{incident_id}`: Reconstructs full chronological lifecycle and causal graph.
- `GET /api/v1/reliability/time-machine/{incident_id}/state-at/{timestamp}`: Point-in-time infrastructure metrics snapshot.
- `GET /api/v1/reliability/time-machine/{incident_id}/causal-graph`: NetworkX causal nodes, edges, and blast radius.

### 6. LangGraph Autonomous Agent Endpoints (`/api/v1/reliability/agent`)
- `POST /api/v1/reliability/agent/assess`: Triggers the 8-node LangGraph reasoning loop with deterministic safety guardrails.
- `GET /api/v1/reliability/agent/last-run`: Returns the cached execution trace and decision of the latest assessment.
