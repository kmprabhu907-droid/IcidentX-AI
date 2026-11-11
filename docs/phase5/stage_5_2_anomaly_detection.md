# IncidentX AI — Phase 5, Stage 5.2: Advanced Anomaly & Resource-Creep Detection Engine

**Status**: Verified & Operational  
**Component**: Perception Layer — Autonomous Reliability Intelligence  
**Author**: Principal SRE Architect & Distributed Systems Engineer  
**Date**: November 2026  

---

## 1. Executive Summary

Stage 5.2 establishes the **Autonomous Perception Layer** of IncidentX AI. Building directly upon the Stage 5.1 high-frequency telemetry collector and 1-minute historical metric rollup storage, Stage 5.2 introduces a modular, explainable statistical and causal anomaly detection engine designed to detect both sudden infrastructure abnormalities and slow, insidious resource degradation ("resource creep").

Every detected anomaly in IncidentX AI is not a raw alert; it is a **synthesized diagnostic finding** that answers 10 structured SRE operational questions, complete with dynamic baseline bounds, EWMA shift tracking, linear trend projections, multi-signal correlation evidence, and an explainable composite confidence score.

---

## 2. Architectural Architecture

The Stage 5.2 detection pipeline sits between the raw telemetry stream/rollup storage and the Phase 3 autonomous investigation orchestrator:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Observability Data Stream                       │
│    (Prometheus Metrics, Ten Golden Signals, 1-Min Historical Rollups)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Stage 5.2: Unified Anomaly Detection Engine              │
│                                                                        │
│  ┌───────────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │   Dynamic Adaptive    │  │  EWMA Tracking   │  │  OLS Sliding   │  │
│  │   Baselines (μ ± 3σ)  │  │ (Rapid Spikes vs │  │ Linear Trends  │  │
│  │ Contamination Guard   │  │ Sustained Shifts)│  │ (Creep & TTE)  │  │
│  └───────────┬───────────┘  └────────┬─────────┘  └───────┬────────┘  │
│              └───────────────┐       │       ┌────────────┘           │
│                              ▼       ▼       ▼                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │     Multi-Signal Correlation & Deterministic Classification      │  │
│  │  (Nominal Bounds, Cross-Metric Clusters, SRE Severity Matrix)    │  │
│  └───────────────────────────────────┬──────────────────────────────┘  │
│                                      │                                 │
│                                      ▼                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Explainable Confidence Engine (C ∈ [0.0, 1.0])       │  │
│  │   (Magnitude, Persistence, Variability, Trend, Corroboration)    │  │
│  └───────────────────────────────────┬──────────────────────────────┘  │
│                                      │                                 │
│                                      ▼                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │      10 Structured SRE Diagnostic Questions & Answers Formulator │  │
│  └───────────────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              Anomaly Lifecycle & Deduplication Service                 │
│         (ACTIVE ➔ ACKNOWLEDGED ➔ RESOLVED ➔ FALSE_POSITIVE)            │
│         (Deduplication by (service, metric) with counter & timestamps)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│          SQLite Database (`anomaly_records`) & REST APIs               │
│          Next.js Frontend: Anomalies & Resource Creep Explorer         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Engine Components

### 3.1. Dynamic Adaptive Baselines (`baseline.py`)
- **Mathematical Model**: Computes sample mean $\mu$ and sample standard deviation $\sigma$ across sliding windows of historical 1-minute rollups ($N \ge 10$).
- **Contamination Prevention**: Prevents in-flight anomalies or chaos injections from polluting the baseline by quarantining values where:
  $$|X_t - \mu| > 3.5 \cdot \sigma \quad \text{or} \quad \frac{|X_t - \mu|}{\max(1.0, \mu)} > 0.50$$
- **History Sufficiency**: Enforces a minimum sample threshold ($N \ge 10$) before activating adaptive $\mu \pm 3\sigma$ bounds. Falls back safely to predefined SRE nominal bounds if $N < 10$.
- **Noise Floor Guard**: Applies an empirical noise floor $\epsilon_{\text{floor}}$ (e.g. 3.0% for percentages, 10ms for latencies) and sets $\sigma_{\text{eff}} = \max(0.5, \sigma)$ to eliminate zero-variance division errors and spurious false alarms on flatlined metrics.

### 3.2. EWMA Rapid Shift Tracking (`ewma.py`)
- **Exponential Smoothing**: Tracks rolling smoothed values using smoothing factor $\alpha = 0.3$:
  $$\text{EWMA}_t = \alpha X_t + (1 - \alpha) \text{EWMA}_{t-1}$$
- **Sudden Spike vs Sustained Shift**:
  - *Sudden Spike*: Current value $X_t$ diverges sharply from $\text{EWMA}_{t-1}$, but EWMA has not caught up ($|X_t - \text{EWMA}_{t-1}| > 2.5 \cdot \sigma_{\text{baseline}}$).
  - *Sustained Shift*: Both $X_t$ and $\text{EWMA}_t$ remain consistently shifted from baseline for $\ge 3$ consecutive ticks.

### 3.3. OLS Linear Trend Analysis (`trend_analysis.py`)
- **Ordinary Least Squares Regression**: Fits linear models over $N$ consecutive rollup observations:
  $$\hat{Y} = \beta_1 t + \beta_0, \quad \beta_1 = \frac{\sum (t_i - \bar{t})(Y_i - \bar{Y})}{\sum (t_i - \bar{t})^2}$$
- **Statistical Significance**: Requires $N \ge 10$ and coefficient of determination $R^2 \ge 0.65$ before flagging deterministic resource creep.
- **Time-to-Exhaustion (TTE)**: For unbounded creep metrics (e.g., `memory_utilization`, `disk_utilization`, `db_pool_utilization`):
  $$\text{TTE} = \frac{\text{Limit} - Y_{\text{current}}}{\beta_1 \cdot 60} \quad (\text{hours})$$
  Flags `CRITICAL` if $\text{TTE} < 2.0\text{ hours}$, `HIGH` if $\text{TTE} < 6.0\text{ hours}$, `MEDIUM` if $\text{TTE} < 24.0\text{ hours}$.

### 3.4. Multi-Signal Correlation & Severity Classification (`rules.py`)
- **Nominal Operational Bounds**: Hard upper/lower safety limits for all 10 Golden Signals.
- **Correlated Metric Clusters**:
  1. *Resource Saturation*: `cpu_utilization` + `latency_p95_ms` / `memory_utilization`
  2. *Connection Exhaustion*: `db_pool_utilization` + `latency_p95_ms` + `error_rate`
  3. *Downstream Dependency Failure*: `dependency_health` degradation + `error_rate` + `latency_p95_ms`
  4. *Traffic Surge Saturation*: `request_rate` + `network_throughput_mbps` + `cpu_utilization`
  5. *Memory Leak Degradation*: Positive slope on `memory_utilization` + degrading `availability_pct`
- **Deterministic Severity Matrix**:
  - `CRITICAL`: Multiple corroborating signals, extreme deviation ($>4\sigma$), nominal breach (e.g. error rate $>5\%$, pool $>95\%$), or $\text{TTE} < 2\text{h}$.
  - `HIGH`: Severe single-signal deviation ($>3\sigma$), significant creep, or $\text{TTE} < 6\text{h}$.
  - `MEDIUM`: Moderate departure ($>2\sigma$), creeping trend with $R^2 \ge 0.65$, or early memory growth.
  - `LOW`: Mild drift outside $2\sigma$ without downstream blast radius.
  - `INFO`: Statistically noticeable deviation without operational impact.

### 3.5. Explainable Confidence Scoring (`confidence.py`)
Calculates composite confidence $C \in [0.0, 1.0]$ based on 6 weighted components:
$$C = 0.25 C_{\text{mag}} + 0.20 C_{\text{pers}} + 0.15 C_{\text{var}} + 0.15 C_{\text{trend}} + 0.15 C_{\text{corrob}} + 0.10 C_{\text{sample}}$$
- $C_{\text{mag}}$: Deviation magnitude relative to baseline noise ($z / 4.0$).
- $C_{\text{pers}}$: Persistence over consecutive evaluation cycles ($\min(1.0, \text{cycles} / 5)$).
- $C_{\text{var}}$: Baseline stability (inversely proportional to baseline coefficient of variation).
- $C_{\text{trend}}$: Consistency of directional drift.
- $C_{\text{corrob}}$: Multi-signal corroboration bonus (+0.20 for 1 correlated signal, +0.35 for $\ge 2$).
- $C_{\text{sample}}$: Sample size adequacy ($N / 30$).

---

## 4. The 10 Structured SRE Diagnostic Questions & Answers

Every anomaly formulated by `UnifiedAnomalyDetector` answers 10 standardized SRE questions:

| # | SRE Diagnostic Question | Engine Formulation |
|---|-------------------------|---------------------|
| 1 | **What happened?** | Clear narrative description of the departure, affected component, and observed delta. |
| 2 | **Which service is affected?** | Microservice identifier, topology node, and runtime role. |
| 3 | **Which metric changed?** | Exact metric name, observed value, expected value, EWMA, and slope. |
| 4 | **What was normal?** | Historical baseline mean $\mu$ and nominal $3\sigma$ range $[\mu - 3\sigma, \mu + 3\sigma]$. |
| 5 | **How big was the departure?** | Absolute deviation, percentage delta, and standard deviation count ($z$-score). |
| 6 | **How long has it been abnormal?** | Duration span in seconds/minutes and total consecutive observation cycles. |
| 7 | **Are other signals corroborating?** | Multi-signal cluster membership and list of coincidentally anomalous metrics. |
| 8 | **How confident is the detection?** | Overall confidence percentage and 6-factor weight breakdown. |
| 9 | **What is the projected impact?** | SRE blast radius, downstream dependency risk, and time-to-exhaustion if unmitigated. |
| 10 | **What should be investigated next?** | Actionable next step (e.g. check trace waterfall, inspect pool logs, verify deployment diff). |

---

## 5. Anomaly Lifecycle Management & Deduplication

Implemented in `AnomalyLifecycleService`:
- **States**: `ACTIVE` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `RESOLVED` (or `FALSE_POSITIVE`).
- **Deduplication Key**: `(service_name, metric_name)` for any anomaly in state `ACTIVE` or `ACKNOWLEDGED`.
- **Deduplication Logic**: When an existing active anomaly is re-observed:
  - `observation_count` is incremented.
  - `last_observed_at` is updated to current UTC timestamp.
  - `observed_value`, `ewma_value`, `trend_slope`, and `confidence` are refreshed.
  - Prevents alert fatigue and database table bloat.
- **Resolution**: When a metric returns to within nominal baseline bounds for $\ge 3$ consecutive cycles, `AnomalyLifecycleService` automatically transitions the anomaly to `RESOLVED`.

---

## 6. Database Schema Extensions

Added to table `anomaly_records` (via migration in `backend/app/core/migration_phase5.py`):

| Column | Type | Description |
|--------|------|-------------|
| `ewma_value` | `Float` | Exponentially smoothed rolling metric value |
| `trend_slope` | `Float` | OLS linear regression slope per second |
| `status` | `String(32)` | Lifecycle status (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`, `FALSE_POSITIVE`) |
| `observation_count` | `Integer` | Number of consecutive observation cycles |
| `first_observed_at` | `DateTime` | UTC timestamp of initial detection |
| `last_observed_at` | `DateTime` | UTC timestamp of most recent observation |

---

## 7. REST API Reference

All endpoints reside under `/api/v1/observability`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/observability/anomalies` | List anomalies with filtering (`service_name`, `severity`, `status`, time range) and pagination |
| `GET` | `/observability/anomalies/{anomaly_id}` | Retrieve comprehensive diagnostic record with the 10 SRE answers |
| `GET` | `/observability/anomalies/active` | Get all currently `ACTIVE` anomalies |
| `PATCH` | `/observability/anomalies/{anomaly_id}/status` | Update anomaly lifecycle status (`ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`, `FALSE_POSITIVE`) |
| `GET` | `/observability/detection/status` | Get detection engine health, active anomaly count, and monitored node count |
| `POST` | `/observability/detection/trigger` | Manually execute an immediate evaluation cycle across all monitored nodes |
| `GET` | `/observability/baselines/{service_identifier}` | Inspect calculated dynamic adaptive baselines ($μ, σ, [min, max], N$) for a service |

---

## 8. Frontend Implementation

Integrated directly into `frontend/app/telemetry/page.tsx`:
- **4th Tab**: "Anomalies & Resource Creep" with an alert counter pill.
- **Engine Status KPI Bar**: Live engine status (`HEALTHY`), active anomaly count, monitored services count, and last evaluation timestamp.
- **Anomalies Feed**:
  - Filterable by service, severity, and status.
  - Visual cards with severity badges (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`), detector type, observed vs expected values, EWMA values, and OLS slope indicators (`TrendingUp` / `TrendingDown`).
  - Interactive confidence bar ($0-100\%$).
- **Deep SRE Diagnostic Panel**:
  - Dedicated display for the 10 SRE structured answers.
  - Interactive lifecycle buttons: `Acknowledge`, `Resolve`, `False Positive`, `Re-activate`.
  - Historical Baseline Inspector: Displays mean $\mu$, std dev $\sigma$, $3\sigma$ bounds, and sample count.
  - Raw Diagnostic Metadata & Supporting Evidence collapsible viewer.

---

## 9. Verification & Test Results

### 9.1. Unit & Anomaly Test Suite (`pytest`)
All 20 Stage 5.2 test scenarios passed:
```
tests/backend/test_stage_5_2_anomaly_detection.py ....................   [100%]
============================== 20 passed in 0.09s ==============================
```

### 9.2. Full Backend Test Suite
All 78 tests across Phases 0–4 and Phase 5 Stages 5.1 & 5.2 passed:
```
======================== 78 passed, 2 warnings in 1.41s ========================
```

### 9.3. Live Integration Verification Script (`scripts/test_integration.py`)
All 28 comprehensive end-to-end integration checks passed:
```
============================================================
🎉 ALL 28 INTEGRATION CHECKS PASSED PERFECTLY!
============================================================
```

### 9.4. Production Build Verification (`npm run build`)
```
✓ Compiled successfully in 1070ms
✓ Linting and checking validity of types
✓ Collecting page data
✓ Generating static pages (10/10)
```
Zero TypeScript or ESLint errors.
