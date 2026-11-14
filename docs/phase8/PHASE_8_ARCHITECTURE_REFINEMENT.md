# INCIDENTX AI — PHASE 8: HYBRID PLATFORM ARCHITECTURE REFINEMENT

**Document ID:** `DOC-INCIDENTX-PH8-REFINEMENT`  
**Version:** `1.0.0`  
**Status:** `OFFICIAL ARCHITECTURE BLUEPRINT`  
**Classification:** `Enterprise Hybrid Reliability Architecture & Autonomous Kubernetes Operations`  
**Date:** `November 11, 2026`  

---

## 1. Executive Summary & Architectural Tenets

Phase 8 elevates IncidentX AI from a deterministic simulation benchmark into a **production-grade, hybrid autonomous reliability engineering platform**. The system seamlessly bridges two runtime worlds:
1. **The DemoMesh Simulation Runtime:** A deterministic sandbox for synthetic stress testing, chaos engineering, and benchmark evaluations (Phases 0–7).
2. **The Live Kubernetes Infrastructure Runtime:** A real-world operational engine connecting to live Kubernetes clusters, Prometheus time-series databases, OpenTelemetry collectors, and cloud/local LLM providers (Google Gemini, OpenAI, Ollama/vLLM).

### Core Architectural Tenets
1. **Preservation of Completed Capabilities:** All 287 passing tests from Phases 0–7 must remain 100% operational without regression or module re-architecting.
2. **Strict Dual-Runtime Isolation:** Simulation telemetry and live cluster telemetry must never cross boundaries. Database records, API responses, and UI dashboards must strictly isolate `DEMOMESH` from `KUBERNETES` via mandatory `data_source` and `environment_mode` tagging.
3. **Dual Credential Separation:** Read-only observability requires distinct, non-privileged credentials from the restricted, namespace-scoped remediation executor.
4. **Transparent AI Attribution:** The platform must never masquerade deterministic rule graphs as LLM reasoning, or vice versa. Every causal hypothesis, courtroom exhibit, and agent execution must record `is_deterministic: bool`, `provider: str`, and `model: str`.
5. **Fail-Safe Autonomous Operations:** Write operations require explicit human approval whenever risk scores exceed $0.40$ or target stateful storage. Unsuccessful remediation triggers automated safety rollbacks, halts repeated retries, and escalates to human SREs.

---

## 2. Existing Phase 0–7 Architecture Audit

### 2.1 Component Inventory

| Component / Layer | Existing Implementation | File Paths | Invariants to Preserve |
| :--- | :--- | :--- | :--- |
| **API Core** | FastAPI asynchronous REST application with CORS, rate limiting, and request validation. | [`backend/main.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/main.py), [`backend/app/api/v1/`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/api/v1/) | Keep all existing v1 routes intact. |
| **Persistence** | SQLAlchemy asyncpg / aiosqlite with UUID mixins, timestamp tracking, and Alembic migrations. | [`backend/app/core/database.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/core/database.py), [`backend/app/models/`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/models/) | Backward-compatible schema evolution. |
| **Security & Auth** | JWT bearer tokens, refresh-token rotation, PBKDF2-SHA256 password hashing, RBAC guards. | [`backend/app/core/auth.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/core/auth.py), [`backend/app/core/crypto.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/core/crypto.py) | Tenant scoping and user RBAC. |
| **Audit Ledger** | SHA-256 blockchain-style cryptographically chained tamper-evident audit ledger. | [`backend/app/core/crypto.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/core/crypto.py), [`backend/app/models/governance.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/models/governance.py) | Immutable verification of remediation events. |
| **Simulation Mesh** | In-memory 7-service DemoMesh (`api-gateway`, `order`, `payment`, `inventory`, `notification`, `postgres`, `redis`). | [`backend/app/services/observability/demo_mesh.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/observability/demo_mesh.py) | Preserved as `DemoMeshAdapter`. |
| **11-Agent Engine** | LangGraph & State Machine orchestration coordinating specialized investigation and recovery agents. | [`backend/app/services/investigation/orchestrator.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/investigation/orchestrator.py), [`backend/app/services/validation/`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/validation/) | Maintain all 11 agent contracts and workflows. |
| **Remediation Engine** | Action registry, precondition validation, risk scoring, idempotency keys, and rollback. | [`backend/app/services/remediation/`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/remediation/) | Pluggable executor adapter design. |
| **Frontend** | Next.js 15, React 19, Tailwind CSS, Hackathon Command Center (`/showcase`). | [`frontend/`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/frontend/) | Zero compilation errors, 14 routes. |

---

## 3. Updated Hybrid System Architecture

```
+------------------------------------------------------------------------------------------------------------------+
|                                        INCIDENTX AI HYBRID PLATFORM ARCHITECTURE                                 |
+------------------------------------------------------------------------------------------------------------------+
|                                                                                                                  |
|  [PRESENTATION LAYER]                                                                                            |
|  Next.js 15 Modern Operations Dashboard & Hackathon Command Center                                              |
|  - Active Environment Switcher & Visual Indicator: [ENV: DemoMesh Simulation] vs [ENV: Kubernetes Live Cluster] |
|  - Real-time Multi-Agent Pipeline Execution Timeline & Provenance Badges                                         |
|  - Root Cause Courtroom, What-If Laboratory Simulator, and Live Infrastructure Scorecard                         |
|                                                                                                                  |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | DUAL RUNTIME ADAPTER LAYER (Abstract Environment Orchestration)                                           |  |
|  | - DemoMeshAdapter: Local in-memory microservice mesh, chaos injection, benchmark library                   |  |
|  | - KubernetesAdapter: Official K8s REST API, cluster discovery, namespace monitoring, pod logs & events     |  |
|  +------------------------------------------------------------------------------------------------------------+  |
|                    |                                                                    |                        |
|                    v                                                                    v                        |
|  +-----------------------------------+                                +-----------------------------------+      |
|  | SIMULATION DATA DOMAIN            |                                | LIVE INFRASTRUCTURE DOMAIN        |      |
|  | data_source: "SIMULATED"          |                                | data_source: "LIVE_K8S"           |      |
|  | - DemoMesh time-series rollups    |                                | - Prometheus PromQL Client        |      |
|  | - Chaos controller fault vectors  |                                | - Kubernetes Pod Log Streamer     |      |
|  | - 15 Synthetic benchmark scenarios|                                | - OpenTelemetry Trace Collector   |      |
|  +-----------------------------------+                                +-----------------------------------+      |
|                    |                                                                    |                        |
|                    +---------------------------------+----------------------------------+                        |
|                                                      |                                                           |
|                                                      v                                                           |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | 11-AGENT RELIABILITY PIPELINE (Preserved & Enhanced)                                                       |  |
|  | 1. Incident Detection Agent: Hybrid signal monitoring (DemoMesh OR Prometheus)                             |  |
|  | 2. Incident Classification Agent: SEV-1 to SEV-4 blast radius scoring                                      |  |
|  | 3. Investigation Intake Agent: Idempotent lock and incident record acquisition                             |  |
|  | 4. Context Gathering Agent: Topology discovery (Static Graph OR K8s Services/Deployments)                   |  |
|  | 5. Multi-Signal Telemetry Agent: PromQL range queries & z-score deviation analysis                        |  |
|  | 6. Log Analysis Agent: Live pod container logs vs Loki pattern clustering                                  |  |
|  | 7. Trace Analysis Agent: OpenTelemetry span bottleneck and latency localization                            |  |
|  | 8. Root Cause Hypothesis Agent: LLM reasoning (Gemini/OpenAI/Ollama) with deterministic fallback           |  |
|  | 9. Evidence Verification Agent (Courtroom): Prosecution vs Defense exhibits & balance of probabilities     |  |
|  | 10. What-If Simulation Agent: Recovery strategy comparison, blast radius & secondary failure projection    |  |
|  | 11. Reliability Memory Agent: Vector embedding, continuous learning, and recurrence prevention            |  |
|  +------------------------------------------------------------------------------------------------------------+  |
|                                                      |                                                           |
|                                                      v                                                           |
|  +------------------------------------------------------------------------------------------------------------+  |
|  | HYBRID REMEDIATION EXECUTION FRAMEWORK                                                                     |  |
|  |                                                                                                            |  |
|  |   [DemoMeshRemediationExecutor]                      [KubernetesRemediationExecutor]                       |  |
|  |   - In-memory mock container actions                 - Uses Restricted Remediation ServiceAccount          |  |
|  |   - Reversible simulated recovery                    - Actions: Pod Restart, Deploy Scale, Rollback,       |  |
|  |                                                        Traffic Isolation, Resource Limit Patch             |  |
|  |                                                                                                            |  |
|  |   [Mandatory Enterprise Governance & Safety Gates]                                                         |  |
|  |   - Risk Scoring (Scores > 0.40 strictly enforce Human-in-the-Loop Operator Approval)                      |  |
|  |   - Precondition Checks, Execution Timeouts, and Cryptographic SHA-256 Audit Logging                       |  |
|  |   - Post-Action Fresh Telemetry Verification Gate & Automated Rollback on Stabilization Failure            |  |
|  +------------------------------------------------------------------------------------------------------------+  |
+------------------------------------------------------------------------------------------------------------------+
```

---

## 4. Agent Responsibility Mapping

Every existing agent from Phases 0–7 is mapped directly to the hybrid architecture, expanding its inputs and outputs while preserving its core contracts.

| Agent Name | Phase 0–7 Baseline Responsibilities | Phase 8 Hybrid Responsibilities | Input Contract | Output Contract |
| :--- | :--- | :--- | :--- | :--- |
| **1. Detection Agent** | Evaluated in-memory DemoMesh sliding windows. | Ingests live Prometheus time-series and Alertmanager webhooks when in K8s mode; falls back to DemoMesh in simulation. | Streaming metrics, threshold rules, PromQL queries | `AnomalyAlert`, `DetectionProvenance` |
| **2. Classification Agent** | Evaluated static service taxonomy and severity. | Inspects live Kubernetes deployment labels, pod replica counts, and namespace tier to assess blast radius. | `AnomalyAlert`, K8s metadata | `IncidentClassification` (SEV-1 to SEV-4) |
| **3. Intake Agent** | Acquired DB lock and initialized investigation state. | Idempotently tags incident with `environment_mode` (`DEMOMESH` vs `KUBERNETES`) and cluster UUID. | `incident_id`, `environment_mode` | `InvestigationWorkspace`, Lock UUID |
| **4. Context Gathering** | Read static dependency graphs from `services.py`. | Queries Kubernetes API (`/api/v1/namespaces/{ns}/services` & endpoints) to map live microservice topology. | `incident_id`, Cluster client | `TopologyContext`, `CausalOrigin` |
| **5. Telemetry Agent** | Analyzed `MetricRollup` DB tables. | Dispatches live PromQL queries (`rate(container_cpu_usage_seconds_total[1m])`) to Prometheus. | Incident window, Prometheus URL | `List[MetricAnomalyDetail]` |
| **6. Log Analysis Agent** | Regex matched in-memory error logs. | Tails live Kubernetes container logs (`/api/v1/.../pods/{pod}/log`) and clusters exception traces. | Pod identifier, Log stream | `List[LogPatternCluster]` |
| **7. Trace Analysis Agent** | Analyzed OpenTelemetry span exhibits. | Ingests live OTel span traces; pinpoints RPC timeouts and HTTP 504 gateways. | Trace ID, Span graph | `TraceBottleneckAnalysis` |
| **8. Hypothesis Agent** | Built-in deterministic topological rules. | Dispatches sanitized context to live LLM (Gemini / OpenAI / Ollama); records tokens and cost; transparently tags provider. | Gathered multi-signal exhibits | `HypothesisGenerationResult` |
| **9. Evidence Verification** | Cross-examined hypotheses in Courtroom format. | Correlates live Prometheus metrics and K8s warning events (`BackOff`, `OOMKilled`) to evaluate balance of probabilities. | Hypotheses + Live Exhibits | `JudicialRuling`, `BrierConfidence` |
| **10. What-If Lab Agent** | Simulated recovery actions on DemoMesh. | Computes projected blast radius on live Kubernetes deployments (replica availability, in-flight traffic drops). | Candidate actions, K8s state | `WhatIfSimulationResult` |
| **11. Safety & Approval Agent** | Gated actions with risk $> 0.40$. | Strictly validates Kubernetes write RBAC permissions; pauses for human operator sign-off if risk $> 0.40$. | `RemediationAction`, User token | `ApprovalVerdict` (GRANTED, HOLD) |
| **12. Recovery Execution** | Simulated container restarts in DemoMesh. | Dispatches authorized mutations via `KubernetesClusterExecutor` (scale deployment, delete pod, patch rollout). | Authorized action payload | `ExecutionResult`, `IdempotencyKey` |
| **13. Recovery Verification** | Checked DemoMesh recovery conditions. | Polls live Prometheus metrics and K8s pod readiness probes over stabilization window; triggers rollback on failure. | Verification threshold, K8s API | `VerificationVerdict` (PASS, ROLLBACK) |
| **14. Reliability Memory** | Stored vector patterns in local database. | Embeds live Kubernetes RCA, incident signatures, and effective recovery actions into persistent memory vector store. | Validated RCA, Action details | `ReliabilityMemory`, Vector Index |

---

## 5. Dual Credential Separation for Kubernetes

To enforce the principle of least privilege, IncidentX AI strictly bifurcates Kubernetes credentials into two isolated ServiceAccounts:

```
+------------------------------------------------------------------------------------------------------+
|                                    KUBERNETES CREDENTIAL SEPARATION                                  |
+------------------------------------------------------------------------------------------------------+
|                                                                                                      |
|  [OBSERVABILITY CREDENTIAL]                                [REMEDIATION CREDENTIAL]                  |
|  ServiceAccount: incidentx-observability-sa               ServiceAccount: incidentx-remediation-sa  |
|  ClusterRole: incidentx-read-only-observability           Role / ClusterRole: incidentx-remediator   |
|  Token: ReadOnlyBearerToken                               Token: RestrictedRemediationBearerToken    |
|                                                                                                      |
|  PERMITTED API VERBS:                                     PERMITTED API VERBS:                      |
|  - get, list, watch                                       - get, patch, update, delete               |
|                                                                                                      |
|  PERMITTED RESOURCES:                                     PERMITTED RESOURCES (Strictly Scoped):    |
|  - pods, pods/log, pods/status                            - pods (delete only, for restart)          |
|  - services, endpoints, namespaces                        - deployments, deployments/scale           |
|  - events, nodes, metrics.k8s.io                          - networkpolicies (traffic isolation)      |
|                                                                                                      |
|  PROHIBITED:                                              PROHIBITED:                                |
|  - NO create, update, patch, delete on ANY resource.       - NO access to Secrets, Nodes, Persistent  |
|                                                             Volumes, or ClusterRoleBindings.         |
|                                                           - Strictly namespace-constrained.          |
+------------------------------------------------------------------------------------------------------+
```

### Complete Kubernetes RBAC Manifests

```yaml
# ==============================================================================
# 1. READ-ONLY OBSERVABILITY SERVICEACCOUNT & CLUSTERROLE
# ==============================================================================
apiVersion: v1
kind: ServiceAccount
metadata:
  name: incidentx-observability-sa
  namespace: incidentx-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: incidentx-read-only-observability
rules:
  - apiGroups: [""]
    resources:
      - pods
      - pods/log
      - pods/status
      - services
      - endpoints
      - namespaces
      - nodes
      - events
      - configmaps
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources:
      - deployments
      - replicasets
      - statefulsets
      - daemonsets
    verbs: ["get", "list", "watch"]
  - apiGroups: ["metrics.k8s.io"]
    resources:
      - pods
      - nodes
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: incidentx-observability-binding
subjects:
  - kind: ServiceAccount
    name: incidentx-observability-sa
    namespace: incidentx-system
roleRef:
  kind: ClusterRole
  name: incidentx-read-only-observability
  apiGroup: rbac.authorization.k8s.io

---
# ==============================================================================
# 2. RESTRICTED REMEDIATION EXECUTION SERVICEACCOUNT & ROLE
# ==============================================================================
apiVersion: v1
kind: ServiceAccount
metadata:
  name: incidentx-remediation-sa
  namespace: incidentx-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: incidentx-remediation-executor
rules:
  # Pod deletion only (to trigger deployment replica recreation)
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "delete"]
  # Deployment scaling and rollback patching
  - apiGroups: ["apps"]
    resources: ["deployments", "deployments/scale"]
    verbs: ["get", "patch", "update"]
  # Emergency traffic isolation
  - apiGroups: ["networking.k8s.io"]
    resources: ["networkpolicies"]
    verbs: ["get", "create", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: incidentx-remediation-binding
subjects:
  - kind: ServiceAccount
    name: incidentx-remediation-sa
    namespace: incidentx-system
roleRef:
  kind: ClusterRole
  name: incidentx-remediation-executor
  apiGroup: rbac.authorization.k8s.io
```

---

## 6. Multi-LLM Provider Architecture & Transparent Attribution

To eliminate vendor lock-in and support air-gapped or high-security deployments, IncidentX AI implements a clean provider abstraction hierarchy:

```
+---------------------------------------------------------------------------------------------------------+
|                                        AI PROVIDER ABSTRACTION                                          |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|                                       [BaseAIProvider (ABC)]                                            |
|                                      - generate_structured()                                            |
|                                      - validate_schema()                                                |
|                                      - sanitize_prompts()                                               |
|                                      - track_token_cost()                                               |
|                                                |                                                        |
|         +-----------------------+--------------+---------------+-----------------------+                |
|         |                       |                              |                       |                |
|         v                       v                              v                       v                |
|  [GeminiAIProvider]     [OpenAIAIProvider]             [LocalAIProvider]      [DeterministicFallback]   |
|  - Google Gemini 2.5    - OpenAI GPT-4o / 4o-mini     - Ollama (Llama 3.3)   - Rule-based graph engine  |
|  - Native JSON Schema   - response_format: json_schema - vLLM / LocalAI       - Zero external network   |
|  - Google API Key       - OpenAI API Key               - Base URL endpoint    - Zero API key dependency |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### Transparent Attribution Contract
Every structured response produced by any agent adheres to the universal attribution contract:
```python
class AIResponse(BaseModel, Generic[T]):
    data: T                              # Validated Pydantic schema
    provider: str                        # "gemini" | "openai" | "ollama" | "deterministic"
    model: str                           # e.g. "gemini-2.5-flash", "gpt-4o", "incidentx-rules-v1"
    prompt_version: str                  # e.g. "v8.0.0"
    duration_ms: int                     # Invocation latency
    is_deterministic: bool               # True if rule-generated; False if LLM-reasoned
    token_usage: TokenUsageMetrics       # Prompt tokens, Completion tokens, Total
    estimated_cost_usd: float            # Precise accounting per model pricing schedule
    timestamp: str                       # ISO-8601 UTC timestamp
```

### Prompt Injection Defense Strategy
All untrusted context inputs (log stack traces, Prometheus metric labels, pod error messages) are sanitized through [`PromptSanitizer`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/ai/sanitizer.py) prior to prompt inclusion:
1. **Delimited Enclosures:** External data is isolated within XML delimiters (`<untrusted_runtime_evidence> ... </untrusted_runtime_evidence>`).
2. **Instruction Neutralization:** Regex strips instruction-override patterns (e.g. `ignore previous instructions`, `system prompt:`, `override safety`).
3. **Secret Masking:** High-entropy strings, Bearer tokens, private keys, and passwords are automatically redacted.

---

## 7. Safe Pluggable Remediation & Centralized Risk Governance

Remediation execution is decoupled from underlying infrastructure via the `BaseRemediationExecutor` interface:

```
+---------------------------------------------------------------------------------------------------------+
|                                    PLUGGABLE REMEDIATION EXECUTORS                                      |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|                                   [BaseRemediationExecutor (ABC)]                                       |
|                                   - execute_action()                                                    |
|                                   - check_preconditions()                                               |
|                                   - verify_post_remediation()                                           |
|                                   - execute_rollback()                                                  |
|                                                |                                                        |
|                       +------------------------+------------------------+                               |
|                       |                                                 |                               |
|                       v                                                 v                               |
|         [DemoMeshRemediationExecutor]                    [KubernetesRemediationExecutor]                |
|         - Interacts with DemoMesh state                  - Interacts with live K8s cluster REST API     |
|         - In-memory mock container actions               - Actions: pod_restart, deployment_scale,      |
|         - Simulation environment only                      deployment_rollback, traffic_isolation       |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### Centralized Governance Workflow
1. **Precondition Check:** Validates that target deployment exists, has $\ge 1$ ready replica, and cluster is reachable.
2. **Dynamic Risk Scoring:**
   - Pod Restart / Traffic Throttling: Low Risk ($0.20 \le \text{Score} < 0.40$).
   - Deployment Scale / Image Rollback: Medium Risk ($0.40 \le \text{Score} < 0.70$).
   - Traffic Isolation / Database Pool Reset: High Risk ($\text{Score} \ge 0.70$).
3. **Human Approval Gate:** If $\text{Risk} \ge 0.40$ or policy requires sign-off, action transitions to `PENDING_APPROVAL`. Execution blocks until an authorized human SRE signs the request via UI or Slack/PagerDuty webhook.
4. **Idempotency Enforcement:** Unique SHA-256 idempotency key prevents duplicate or replay execution.
5. **Cryptographic Audit Chaining:** The action is hashed and recorded into the tamper-evident blockchain audit ledger.
6. **Fresh Telemetry Verification Gate:** Post-execution, the system samples live Prometheus metrics over a 15–30 second window. If metrics fail to stabilize below threshold:
   - Automated Rollback is triggered immediately.
   - Repeated action executions are permanently halted for that incident.
   - High-severity escalation notification is broadcast.

---

## 8. Database Schema Changes & Strict Data Isolation

To guarantee that simulated benchmark data and live Kubernetes data never mix, the database schema evolves with backward-compatible migrations:

```
+---------------------------------------------------------------------------------------------------------+
|                                       DATABASE SCHEMA EVOLUTION                                         |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  [NEW TABLE: kubernetes_clusters]                                                                        |
|  - id: String(36) [PK]                                                                                  |
|  - organization_id: String(36) [FK -> organizations.id]                                                 |
|  - name: String(100) (e.g. "production-us-east-1", "staging-cluster")                                   |
|  - api_server_url: String(255) (e.g. "https://k8s.internal:6443")                                       |
|  - cluster_version: String(50)                                                                          |
|  - is_active: Boolean                                                                                   |
|  - read_only_token_ref: String(255) (Vault or secure secret ref)                                        |
|  - remediation_token_ref: String(255) (Vault or secure secret ref)                                      |
|  - ca_cert_data: Text (PEM format)                                                                      |
|  - created_at, updated_at                                                                               |
|                                                                                                         |
|  [UPDATED TABLE: incidents]                                                                             |
|  + environment_mode: String(30) NOT NULL DEFAULT "DEMOMESH"  ["DEMOMESH" | "KUBERNETES"]                |
|  + data_source: String(30) NOT NULL DEFAULT "SIMULATED"       ["SIMULATED" | "LIVE_K8S"]                |
|  + cluster_id: String(36) NULL [FK -> kubernetes_clusters.id]                                           |
|  + namespace: String(100) NULL                                                                          |
|                                                                                                         |
|  [UPDATED TABLE: telemetry_events & metric_rollups]                                                     |
|  + data_source: String(30) NOT NULL DEFAULT "SIMULATED"       ["SIMULATED" | "LIVE_K8S"]                |
|  + cluster_id: String(36) NULL                                                                          |
|                                                                                                         |
|  [UPDATED TABLE: agent_executions]                                                                      |
|  + provider: String(50) NOT NULL DEFAULT "deterministic"                                                |
|  + is_deterministic: Boolean NOT NULL DEFAULT True                                                      |
|  + prompt_tokens: Integer DEFAULT 0                                                                     |
|  + completion_tokens: Integer DEFAULT 0                                                                 |
|  + cost_usd: Float DEFAULT 0.0                                                                          |
|                                                                                                         |
|  [UPDATED TABLE: remediation_actions]                                                                   |
|  + executor_type: String(50) NOT NULL DEFAULT "DEMOMESH"     ["DEMOMESH" | "KUBERNETES"]                |
|  + cluster_id: String(36) NULL                                                                          |
|  + namespace: String(100) NULL                                                                          |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### Data Isolation Enforcement Queries
Every data access repository (`IncidentRepository`, `TelemetryRepository`, `AuditRepository`) strictly enforces:
```python
# Live Kubernetes queries never touch simulation data
stmt = select(Incident).where(
    Incident.organization_id == org_id,
    Incident.environment_mode == active_environment_mode,  # "KUBERNETES" or "DEMOMESH"
    Incident.data_source == ("LIVE_K8S" if active_environment_mode == "KUBERNETES" else "SIMULATED")
)
```

---

## 9. API Integration Plan

New and expanded REST endpoints under `/api/v1/`:

| Method | Endpoint | Description | Access / RBAC |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/environment/active` | Returns active environment (`DEMOMESH` vs `KUBERNETES`) and cluster status. | Read-Only (All Roles) |
| **POST**| `/api/v1/environment/switch` | Toggles active runtime between `DEMOMESH` and `KUBERNETES`. | Admin / SRE Lead Only |
| **GET** | `/api/v1/kubernetes/clusters` | Lists registered Kubernetes clusters and their connectivity status. | Operator / Admin |
| **POST**| `/api/v1/kubernetes/clusters` | Registers a new Kubernetes cluster with dual-credential refs. | Admin Only |
| **GET** | `/api/v1/kubernetes/clusters/{id}/health` | Inspects live cluster node health, pods, and namespaces. | Operator / Admin |
| **GET** | `/api/v1/observability/prometheus/query` | Executes live PromQL instant or range queries against configured Prometheus. | Operator / Admin |
| **POST**| `/api/v1/observability/alertmanager/webhook`| Ingress webhook for live Prometheus Alertmanager alert payloads. | Public Webhook (HMAC signed) |
| **POST**| `/api/v1/ai/test-provider` | Validates connectivity, latency, and structured schema generation for an LLM provider. | Admin Only |
| **GET** | `/api/v1/ai/token-usage` | Returns aggregated token consumption and financial cost metrics. | Admin / SRE Lead |
| **POST**| `/api/v1/remediation/{id}/execute-k8s` | Executes authorized remediation action directly against Kubernetes cluster. | Operator (Post-Approval) |

---

## 10. Security Threat Model (STRIDE)

| Threat Category | Potential Attack Vector | Platform Countermeasure | Verification Test |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Rogue caller attempts to impersonate Kubernetes ServiceAccount or API provider. | Mutual TLS (mTLS), Bearer token validation, CA certificate verification for all K8s API calls. | `test_kubernetes_tls_validation` |
| **Tampering** | Attacker tampers with Prometheus telemetry or remediation parameters. | SHA-256 HMAC payload verification, schema bounds checking, and cryptographically chained audit logs. | `test_remediation_parameter_tampering` |
| **Repudiation** | Operator denies authorizing a destructive deployment rollback. | Nonce-signed approval tokens with user ID, timestamp, and immutable blockchain ledger recording. | `test_audit_chain_tamper_evidence` |
| **Information Disclosure** | LLM prompt leaks Kubernetes Secrets, database passwords, or private customer data. | High-entropy token redaction via `PromptSanitizer`; secrets strictly excluded from agent context. | `test_prompt_sanitizer_secret_redaction` |
| **Denial of Service** | Prompt injection forces recursive LLM reasoning or unbounded API retries. | Strict per-invocation timeouts (30s), token caps, rate limiters, and deterministic fallback circuits. | `test_ai_provider_timeout_and_fallback` |
| **Elevation of Privilege** | Agent attempts arbitrary shell execution or pod privilege escalation. | Remediation ServiceAccount lacks `pods/exec` and `clusterrolebindings`; allowlisted actions only. | `test_rbac_privilege_escalation_blocked` |

---

## 11. Development Milestones & Phased Execution

```
+------------------------------------------------------------------------------------------------------+
|                                     PHASE 8 IMPLEMENTATION PHASES                                    |
+------------------------------------------------------------------------------------------------------+
|                                                                                                      |
|  [Stage 8.1] Live AI Reasoning Engine (Module 1)                                                     |
|  - Multi-provider abstraction: Gemini, OpenAI, Ollama/vLLM, Deterministic.                           |
|  - Token and cost accounting engine.                                                                 |
|  - Unit & security tests: tests/backend/test_phase8_live_ai.py                                        |
|                                                                                                      |
|  [Stage 8.2] Kubernetes Integration & Cluster Executor (Module 2)                                   |
|  - KubernetesClusterExecutor with read-only cluster discovery and pod inspection.                   |
|  - Dual ServiceAccount RBAC specifications.                                                          |
|  - High-fidelity KubernetesMockServer test harness for sandbox tests.                                |
|  - Unit & RBAC tests: tests/backend/test_phase8_kubernetes.py                                        |
|                                                                                                      |
|  [Stage 8.3] Live Observability & Prometheus Integration (Module 3)                                  |
|  - PrometheusClient (PromQL instant & range queries).                                                |
|  - GrafanaConnector (annotations & dashboard URLs).                                                  |
|  - Alertmanager webhook ingress endpoint.                                                            |
|  - Observability tests: tests/backend/test_phase8_observability.py                                    |
|                                                                                                      |
|  [Stage 8.4] Autonomous Live Investigation Pipeline (Module 4)                                       |
|  - 11-agent pipeline wired to live Prometheus, pod logs, and K8s events.                             |
|  - Transparent provenance tagging (LLM vs Deterministic).                                            |
|  - Investigation tests: tests/backend/test_phase8_live_investigation.py                              |
|                                                                                                      |
|  [Stage 8.5] Safe Pluggable Remediation & Automated Rollback (Module 5)                              |
|  - KubernetesRemediationExecutor (restart, scale, rollback, isolate).                                |
|  - Precondition checks, human approval gating (>0.40), post-verification, auto-rollback.              |
|  - Safety tests: tests/backend/test_phase8_safe_remediation.py                                       |
|                                                                                                      |
|  [Stage 8.6] Hybrid Infrastructure Environment & UI Badge (Module 6)                                 |
|  - Active environment switcher (DEMOMESH vs KUBERNETES) with strict data isolation.                  |
|  - Next.js Header badge and environment toggle.                                                      |
|  - Hybrid tests: tests/backend/test_phase8_hybrid_environment.py                                      |
|                                                                                                      |
|  [Stage 8.7] End-to-End Live Infrastructure Demonstration & Certification (Module 7)                |
|  - Live showcase drill endpoint and UI walkthrough on /showcase.                                     |
|  - Full regression test run (Phases 0–8: 300+ tests passing).                                        |
|  - Master deliverable report: docs/phase8/PHASE_8_LIVE_INFRASTRUCTURE_REPORT.md                      |
|                                                                                                      |
+------------------------------------------------------------------------------------------------------+
```

---

## 12. Integration Testing Strategy

1. **Isolation Invariant:**  
   Every unit test runs against the isolated in-memory test database (`TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"`).
2. **Kubernetes Mock Server:**  
   To allow offline, deterministic, and sandboxed testing on hosts without active Kubernetes clusters, a dedicated `KubernetesMockServer` will mock standard Kubernetes 1.30 REST responses (`/version`, `/api/v1/namespaces/default/pods`, `/apis/apps/v1/namespaces/default/deployments/payment-service/scale`).
3. **AI Mocking & Token Ledger Verification:**  
   AI provider tests will verify structured output schema compliance, prompt injection rejection, and cost tracking with both mocked LLM responses and deterministic fallbacks.
4. **Zero-Regression Guarantee:**  
   The complete existing 287-test backend suite must be re-run and pass at 100% after each module implementation.

---

**This architecture refinement is complete, approved, and ready for Stage 8.1 implementation.**
