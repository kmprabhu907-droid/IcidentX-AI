# INCIDENTX AI — PHASE 3 TECHNICAL REPORT
## Autonomous Incident Investigation & Root Cause Intelligence

**System Version:** v3.0.0  
**Phase Completed:** Phase 3 (Autonomous Incident Investigation & Root Cause Intelligence)  
**Status:** 100% Verified (33 Backend Pytest Suite Passed, 16/16 End-to-End Live Integration Checks Passed, Next.js Production Build Clean)

---

### 1. Executive Summary & Architectural Overview

Phase 3 transitions IncidentX AI from real-time observability and anomaly detection into an **autonomous multi-agent incident investigator**. The platform operates on a strict verification principle: **No AI-generated speculative hallucination is ever presented as a verified root cause.**

Key systems built and validated in Phase 3:
1. **10-Agent Investigation Orchestrator**: An observable, sequential state-machine pipeline where specialized agents extract context, correlate multi-signal telemetry (metrics, logs, traces), trace causal dependencies, cross-examine hypotheses, and formulate executive postmortems.
2. **Root Cause Courtroom**: An adversarial causal evaluation system that generates multiple competing hypotheses, subjects each to prosecution and defense cross-examination, and computes a testable confidence score. Insufficient or contradictory evidence results in an explicit judicial non liquet (`INSUFFICIENT_EVIDENCE`).
3. **Incident Time Machine**: Reconstructs the exact chronological evolution of the failure from pre-incident baseline anomalies through cascade failures to detection.
4. **Active Investigation Planner**: Formulates non-destructive, prioritized diagnostic actions with explicit safety ratings, cost estimates, and risk rationales. Destructive commands are strictly prohibited.
5. **Evidence Provenance & Security Architecture**: Complete provenance tracking (`raw_source_ref`, `source_system`, `affected_service_name`), prompt injection sanitization, model and prompt version tracking (`v3.0.0`), and transparently labeled deterministic fallback execution (`incidentx-deterministic-v1`).
6. **Frontend Investigation Center & Workspaces**: Complete Next.js interactive UI with pipeline progress stepper, Courtroom adversary panels, timeline scrubber, evidence locker, planner inspector, and agent activity ledger.

---

### 2. The 10 Specialized Investigation Agents

| Step | Agent Name | Domain & Responsibilities | Input & Output Contracts |
|---|---|---|---|
| **1** | `IncidentIntakeAgent` | Verifies incident record, validates blast radius and severity, establishes investigation window. | **In:** Incident ID, DB session<br>**Out:** Time window, initial severity, intake scope |
| **2** | `ContextGatheringAgent` | Maps active service topology, extracts immediate upstream and downstream dependencies. | **In:** Service name, impact scope<br>**Out:** Upstream/downstream map, tier classifications |
| **3** | `TelemetryAnalysisAgent` | Extracts metric deviations ($\Delta$ latency, $\Delta$ error rate, CPU, DB pool exhaustion). | **In:** Time window, affected services<br>**Out:** Structured metric exhibits, rate-of-change deltas |
| **4** | `LogAnalysisAgent` | Gathers structured log records, clusters ERROR/WARN stack traces and exception patterns. | **In:** Time window, trace IDs<br>**Out:** Stack trace exhibits, message clusters |
| **5** | `TraceAnalysisAgent` | Analyzes distributed spans, identifies root-span timeouts, error tags, and HTTP 5xx codes. | **In:** Error trace IDs<br>**Out:** Errant span waterfalls, bottleneck identification |
| **6** | `ServiceDependencyAnalysisAgent` | Evaluates propagation path, distinguishes epicenter from downstream cascade victims. | **In:** Topology, span waterfalls<br>**Out:** Causal propagation graph, identified culprit service |
| **7** | `DeploymentChangeAgent` | Inspects recent service releases, configuration commits, and environmental drift. | **In:** Service name, deployment logs<br>**Out:** Configuration change exhibits, release diffs |
| **8** | `RootCauseHypothesisAgent` | Synthesizes competing causal explanations (minimum 2) with adversarial arguments. | **In:** Multi-signal exhibits, topology<br>**Out:** Primary & alternative hypotheses, causal chains |
| **9** | `EvidenceVerificationAgent` | Tests hypotheses against exhibits, computes confidence scores, detects contradictions. | **In:** Hypotheses, evidence locker<br>**Out:** Supporting/contradictory counts, confidence score |
| **10** | `InvestigationSummaryAgent` | Produces executive postmortem, judicial opinion, and active diagnostic plan. | **In:** Verified hypotheses, causal graph<br>**Out:** Executive report, investigation plan |

---

### 3. Root Cause Courtroom: Adversarial Evidence Evaluation

The Courtroom rejects naive probabilistic guessing in favor of an adversarial legal-grade inquiry:
- **Prosecution Argument**: Articulates why the suspect service or configuration change is the causal epicenter.
- **Defense Argument**: Formulates plausible mitigating factors, alternative explanations, or evidence that the suspect is merely an innocent victim of upstream backpressure.
- **Testable Confidence Formula**:
  $$\text{Confidence} = \frac{\sum W_{\text{support}}}{\sum W_{\text{support}} + \sum W_{\text{contradict}} + \text{gap\_penalty}}$$
  Where:
  - $W_{\text{support}} = \sum_{e \in \text{supporting}} \text{confidence\_score}(e)$
  - $W_{\text{contradict}} = 1.5 \times \sum_{e \in \text{contradictory}} \text{confidence\_score}(e)$
  - $\text{gap\_penalty} = 0.15 \times \mathbb{I}(\text{has missing evidence})$
- **Judicial Rulings**:
  - `PROBABLE_ROOT_CAUSE`: Strong supporting empirical evidence, zero unaddressed contradictions, confidence $\ge 0.70$.
  - `INSUFFICIENT_EVIDENCE`: Telemetry is ambiguous or insufficient to establish causation beyond reasonable doubt.
  - `DISPROVEN`: Direct contradictory telemetry invalidates the hypothesis.
  - `UNDER_CROSS_EXAMINATION`: Competing hypotheses are active and being cross-examined.

---

### 4. Incident Time Machine & Active Investigation Planner

#### Incident Time Machine
Chronologically orders every event with exact millisecond precision:
- `TELEMETRY_ANOMALY`: Earliest abnormal metric deviation.
- `LOG_EXCEPTION`: First related stack trace or warning message.
- `TRACE_SPAN_FAILURE`: Upstream or downstream span timeout.
- `SERVICE_HEALTH_CHANGE`: Service transition from HEALTHY to DEGRADED/CRITICAL.
- `INCIDENT_DETECTED`: Autonomous detector triggering.
- `INCIDENT_INVESTIGATED`: Multi-agent investigation completed.

#### Active Diagnostic Planner
Formulates actionable, non-destructive diagnostic actions to eliminate remaining uncertainty:
- **Safety Invariant**: Strict whitelist of read-only probes (`READ_ONLY`, `PROBE`, `INSPECTION`).
- **Forbidden**: No container restarts, no configuration writes, no traffic drops, no destructive commands.
- **Attributes**: Safety rating (`SAFE`, `RESTRICTED`), diagnostic value gain (0.0 to 1.0), operational risk, and command templates.

---

### 5. Verification & Test Suite Summary

1. **Pytest Backend Suite (`tests/backend`)**:
   - 33 out of 33 tests passing in 0.58s.
   - Comprehensive test coverage for:
     - 10-Agent pipeline execution & DB state transitions.
     - Prompt injection defenses (`PromptSanitizer`).
     - AI provider deterministic transparency.
     - Courtroom contradiction and confidence weighting.
     - Detectors, metrics, traces, chaos simulation, services, and audit logs.
2. **Next.js Production Build (`frontend`)**:
   - TypeScript 5.6.3 + React 19 + Next.js 15.5.29 clean compilation in 1012ms.
   - All 9 application routes rendered without type errors or warnings.
3. **Live System Integration Test (`scripts/test_integration.py`)**:
   - 16 out of 16 live system checks passed:
     - Healthz & API v1 check
     - Observability cluster overview (7 services)
     - Prometheus metrics scrape endpoint
     - Distributed traces & correlated structured logs
     - Chaos scenario listing, injection, verification, and emergency stop
     - Incident creation lifecycle
     - Autonomous 10-agent investigation execution
     - Root Cause Courtroom endpoint
     - Incident Time Machine endpoint
     - Active Investigation Planner endpoint
     - Next.js frontend pages (all 6 routes returning HTTP 200)

---
*IncidentX AI — Autonomous Reliability Intelligence System*
