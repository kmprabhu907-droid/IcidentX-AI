# INCIDENTX AI — PHASE 8: ARCHITECTURE AUDIT & HYBRID INFRASTRUCTURE PLAN

**Document ID:** `DOC-INCIDENTX-PH8-AUDIT`  
**Version:** `1.0.0`  
**Status:** `AUDIT COMPLETE & APPROVED`  
**Classification:** `Enterprise Production Readiness & Real-World Hybrid Autonomous Operations`  
**Date:** `November 11, 2026`  

---

## 1. Executive Summary & Phase 8 Mission

IncidentX AI has established a complete, empirically benchmarked, and verified reliability platform across Phases 0–7 (287/287 passing tests, 100% pass rate). Until Phase 7, the application has operated primarily against an internal, in-memory microservice simulation engine (**DemoMesh**), utilizing deterministic graph-based reasoning alongside prototype LLM client interfaces.

The mission of **Phase 8: Real-World Autonomous Infrastructure Integration** is to transition IncidentX AI into a **hybrid, dual-engine reliability platform** capable of connecting directly to **live Kubernetes clusters, real Prometheus/Grafana observability stacks, OpenTelemetry trace streams, and production-grade LLMs (Google Gemini, OpenAI, and local Ollama/vLLM endpoints)** while rigorously preserving the isolated DemoMesh sandbox.

```
+---------------------------------------------------------------------------------------------------------+
|                                    INCIDENTX AI PHASE 8 HYBRID PLATFORM                                 |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  [USER & SRE INTERFACE]  <----> Next.js Command Center (Active Environment Badge: DemoMesh | K8s Live)  |
|                                                                                                         |
|  +---------------------------------------------------------------------------------------------------+  |
|  | DUAL-ENVIRONMENT ABSTRACTION LAYER                                                               |  |
|  | - Mode A: DemoMesh Simulation Engine (Isolated local testing, chaos drills, benchmarks)           |  |
|  | - Mode B: Kubernetes Live Cluster Engine (Official K8s REST API, read-only RBAC, live workloads)  |  |
|  +---------------------------------------------------------------------------------------------------+  |
|              |                                                                 |                        |
|              v                                                                 v                        |
|  [Simulated Telemetry (DemoMesh)]                             [Live Infrastructure Connectors]          |
|  - In-memory service state                                    - Prometheus PromQL Query Client          |
|  - Chaos injection controller                                 - Kubernetes Pod Log & Event Streamer     |
|  - Benchmark scenario library                                 - OpenTelemetry Trace Collector           |
|                                                               - Grafana Annotation Dispatcher           |
|              |                                                                 |                        |
|              +--------------------------------+--------------------------------+                        |
|                                               |                                                         |
|                                               v                                                         |
|  +---------------------------------------------------------------------------------------------------+  |
|  | 11-AGENT RELIABILITY PIPELINE & LIVE AI REASONING                                                 |  |
|  | 1. Detection  2. Classification  3. Intake  4. Context  5. Telemetry  6. Logs  7. Traces          |  |
|  | 8. Hypothesis  9. Courtroom Verification  10. What-If Lab  11. Reliability Memory                 |  |
|  |                                                                                                   |  |
|  | [AI Provider Abstraction]                                                                         |  |
|  | Primary: Google Gemini / OpenAI  --> Secondary: Local (Ollama/vLLM) --> Fallback: Deterministic  |  |
|  | Enforces: Token Cost Accounting, JSON Schema Validation, Prompt Sanitization, Transparent Tagging |  |
|  +---------------------------------------------------------------------------------------------------+  |
|                                               |                                                         |
|                                               v                                                         |
|  +---------------------------------------------------------------------------------------------------+  |
|  | SAFE PLUGGABLE REMEDIATION FRAMEWORK                                                              |  |
|  | - DemoMesh Executor: In-memory container manipulation & state restoration                         |  |
|  | - KubernetesClusterExecutor: Pod Restart | Deployment Scale | Rollback | Traffic Isolation       |  |
|  | - Mandatory Guardrails: Preconditions, Risk Scoring (>0.40 requires human approval), Idempotency, |  |
|  |   Timeouts, Post-action Telemetry Verification, Automatic Rollback on Failure                      |  |
|  +---------------------------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Comprehensive Codebase Audit (Phases 0–7 Baseline)

### 2.1 Existing Architecture Assets
- **Backend Core:** FastAPI (`backend/main.py`), SQLAlchemy asyncpg/aiosqlite (`backend/app/core/database.py`), Pydantic v2 settings.
- **Security & Multi-Tenancy:** JWT authentication, RBAC policy guards (`backend/app/core/auth.py`), tenant isolation resolver (`backend/app/core/tenant.py`), cryptographic audit ledger (`backend/app/core/crypto.py`).
- **Investigation Pipeline:** 10-agent orchestration state machine (`backend/app/services/investigation/orchestrator.py`) + Reliability Memory Agent (`backend/app/services/reliability_memory/engine.py`).
- **Courtroom & What-If:** Prosecution vs defense exhibit evaluation (`backend/app/services/validation/courtroom_validator.py`), 7-strategy recovery simulation (`backend/app/services/validation/what_if_validator.py`).
- **Frontend Dashboard:** Next.js 15, Tailwind CSS, TypeScript (`frontend/`), Hackathon Command Center (`frontend/app/showcase/page.tsx`).
- **Test Integrity:** 287 passed backend tests, 0 failed, 0 skipped. Full suite execution duration: ~23s.

---

## 3. Gap Analysis Across the 7 Mandated Phase 8 Modules

### Module 1: Live AI Reasoning
- **Current State:** `AIProviderClient` (`backend/app/services/ai/provider.py`) supports only `"deterministic"` mode or a basic OpenAI completion call. Gemini is not implemented. Local models (Ollama/vLLM) are not implemented. Token usage and cost tracking are absent.
- **Required Architecture:**
  - Pluggable provider hierarchy: `BaseAIProvider`, `GeminiAIProvider` (via official `https://generativelanguage.googleapis.com` REST API), `OpenAIAIProvider`, `LocalAIProvider` (Ollama/vLLM OpenAI-compatible endpoints), and `DeterministicFallbackProvider`.
  - Structured output enforcement using Pydantic schema validation with automatic repair retries.
  - Token and financial cost accounting (`TokenCostTracker`) tracking prompt tokens, completion tokens, model tier, and estimated USD cost per agent run.
  - Multi-tier fallback chain: Gemini/OpenAI &rarr; Local AI &rarr; Deterministic rule graph.
  - Transparent tagging: Output models must explicitly indicate `is_deterministic: bool` and `provider: str`.

### Module 2: Kubernetes Integration
- **Current State:** Zero Kubernetes API client logic exists in the codebase. All actions operate on `demo_mesh`.
- **Required Architecture:**
  - `KubernetesClusterExecutor`: Async REST client connecting to Kubernetes cluster endpoints via standard Kubeconfig or in-cluster ServiceAccount token/CA cert.
  - Cluster Discovery: Query cluster version (`/version`), nodes (`/api/v1/nodes`), namespaces (`/api/v1/namespaces`).
  - Namespace & Resource Inspection: Pod health, phases (Running, CrashLoopBackOff, Pending, Error), container statuses, restart counts, termination reasons (`OOMKilled`, `Error`), deployment replica status (`/apis/apps/v1/namespaces/{ns}/deployments`).
  - Kubernetes Event Collection: Stream Warning and Normal events (`FailedScheduling`, `Unhealthy`, `BackOff`, `Killing`).
  - Least-Privilege RBAC: Default to read-only roles (`ClusterRole` with `get`, `list`, `watch` on pods, services, deployments, events).
  - High-Fidelity Test Sandbox: In-memory mock Kubernetes API server (`KubernetesMockServer`) to allow comprehensive automated testing when no physical cluster is present.

### Module 3: Live Observability
- **Current State:** Telemetry is generated primarily by `demo_mesh.py`. An export endpoint exists at `/api/v1/telemetry/prometheus`, but no PromQL client queries external Prometheus servers.
- **Required Architecture:**
  - `PrometheusClient`: Query live Prometheus instances via instant (`/api/v1/query`) and range (`/api/v1/query_range`) APIs.
  - Standard PromQL queries: CPU utilization (`rate(container_cpu_usage_seconds_total[1m])`), memory saturation (`container_memory_working_set_bytes`), HTTP request rates, P95/P99 latencies, and 5xx error spikes.
  - `GrafanaConnector`: Deep-link generation and incident annotation dispatch (`/api/annotations`).
  - Live Pod Log Streamer: Query `/api/v1/namespaces/{ns}/pods/{pod}/log` with regex pattern clustering.
  - Live Alert Integration: Webhook ingestion endpoint for Prometheus Alertmanager (`/api/v1/alerts/alertmanager`).

### Module 4: Autonomous Investigation against Real Signals
- **Current State:** The 11-agent pipeline gathers evidence from `demo_mesh` snapshots.
- **Required Architecture:**
  - Update `InvestigationOrchestrator` agents:
    - `TelemetryAnalysisAgent`: Queries live Prometheus if `ENVIRONMENT == "KUBERNETES"`.
    - `LogAnalysisAgent`: Queries live Kubernetes pod logs.
    - `ContextGatheringAgent`: Discovers topology directly from Kubernetes Service and Deployment graphs.
    - `RootCauseHypothesisAgent`: Generates competing hypotheses using live LLMs (Gemini/OpenAI) with explicit token tracking.
    - `EvidenceVerificationAgent`: Correlates live Prometheus metric exhibits and K8s event exhibits in Courtroom format.

### Module 5: Safe Remediation Execution
- **Current State:** `RemediationExecutor` mutates `demo_mesh` container objects.
- **Required Architecture:**
  - Pluggable `RemediationExecutor` interface with two implementations:
    1. `DemoMeshRemediationExecutor` (Simulated actions).
    2. `KubernetesRemediationExecutor` (Live Kubernetes actions).
  - Live Kubernetes Actions supported:
    - `pod_restart`: Delete pod with grace period, allowing ReplicaSet to recreate it safely.
    - `deployment_scale`: Patch deployment replica count via `/apis/apps/v1/namespaces/{ns}/deployments/{name}/scale`.
    - `deployment_rollback`: Undo rollout or revert container image tag.
    - `traffic_isolation`: Route traffic away by applying canary label or isolation NetworkPolicy.
    - `resource_adjustment`: Adjust container CPU/memory limits.
  - Safety Invariants:
    - Precondition checks (e.g. cluster reachable, minimum ready replicas > 1).
    - Human-in-the-loop approval gate for any write operation or risk score $> 0.40$.
    - Rollback mechanism: Snapshot pre-action replica/spec and automatically restore if post-action verification fails.

### Module 6: Hybrid Infrastructure Architecture
- **Current State:** Single global simulation environment.
- **Required Architecture:**
  - Environment Switcher: Configurable via `ACTIVE_ENVIRONMENT` setting (`"DEMOMESH"` vs `"KUBERNETES"`).
  - Data Tagging: Strict database column `data_source` (`"SIMULATED"` vs `"LIVE_K8S"`). Queries in DemoMesh never touch live data, and vice versa.
  - UI Visualization: Persistent Header Badge indicating active mode (`[ENV: DemoMesh Simulation]` vs `[ENV: Kubernetes Live Cluster]`) with 1-click toggle where permitted by RBAC.

### Module 7: Live Infrastructure Demonstration
- **Current State:** Showcase Command Center runs against benchmark library.
- **Required Architecture:**
  - Dedicated `/showcase/kubernetes` workflow demonstrating the complete 11-step autonomous loop against real K8s pod signals with controlled chaos fault injection.

---

## 4. Implementation Roadmap & Staged Rollout

We will implement Phase 8 sequentially, testing and verifying every module independently:

1. **Stage 8.1 — Live AI Reasoning Engine (Module 1)**
   - Implement `backend/app/services/ai/providers/` (`GeminiProvider`, `OpenAIProvider`, `LocalAIProvider`, `DeterministicFallbackProvider`).
   - Implement `TokenCostTracker` and token ledger.
   - Implement multi-tier fallback chain.
   - Create unit & security tests in `tests/backend/test_phase8_live_ai.py`.

2. **Stage 8.2 — Kubernetes Integration & Cluster Executor (Module 2)**
   - Implement `KubernetesClient` and `KubernetesClusterExecutor` (`backend/app/services/kubernetes/`).
   - Implement cluster discovery, pod health, deployment status, restart tracking, and event streaming.
   - Implement read-only RBAC governance.
   - Build `KubernetesMockServer` for sandbox testing.
   - Create tests in `tests/backend/test_phase8_kubernetes.py`.

3. **Stage 8.3 — Live Observability & Prometheus Integration (Module 3)**
   - Implement `PrometheusClient` and `GrafanaConnector` (`backend/app/services/observability/prometheus.py`).
   - Implement Alertmanager webhook ingestion.
   - Create tests in `tests/backend/test_phase8_observability.py`.

4. **Stage 8.4 — Autonomous Live Investigation (Module 4)**
   - Wire live K8s telemetry, pod logs, and Prometheus metrics into the 11-agent pipeline.
   - Ensure clear distinction between LLM reasoning and deterministic rules.
   - Create tests in `tests/backend/test_phase8_live_investigation.py`.

5. **Stage 8.5 — Safe Pluggable Remediation (Module 5)**
   - Implement `KubernetesRemediationExecutor` with pod restart, deployment scale, rollback, and isolation.
   - Implement pre/post verification and automatic rollback.
   - Create tests in `tests/backend/test_phase8_safe_remediation.py`.

6. **Stage 8.6 — Hybrid Environment Management (Module 6)**
   - Add environment selector, data separation enforcement, and frontend header badge.
   - Update Next.js frontend with live environment toggle.
   - Create tests in `tests/backend/test_phase8_hybrid_environment.py`.

7. **Stage 8.7 — End-to-End Live Infrastructure Showcase (Module 7)**
   - Build live demonstration endpoint and UI walkthrough on `/showcase`.
   - Author master deliverable `docs/phase8/PHASE_8_LIVE_INFRASTRUCTURE_REPORT.md`.
   - Run complete test suite (Phases 0–8).
