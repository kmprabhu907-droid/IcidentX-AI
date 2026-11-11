# INCIDENTX AI — PHASE 5, STAGE 5.1
## Observability Data Pipeline Architecture & Implementation Guide

**Document Version:** 1.0.0  
**Phase:** 5 (Continuous Reliability Intelligence & Regression Detection)  
**Stage:** 5.1 (Observability Data Pipeline)  
**Status:** IMPLEMENTED & TESTED  
**Workspace:** `backend/app/services/observability/`  

---

### 1. Executive Summary

Stage 5.1 delivers the foundational **Continuous Observability Data Pipeline** for IncidentX AI Phase 5. The pipeline continuously monitors the 7-node microservice simulation mesh (`DemoMesh`), aggregates 10 Golden Reliability Signals into 1-minute time-bucket statistical rollups, stores downsampled historical metrics in the relational database, and automatically enforces a rolling 7-day retention policy to eliminate unbounded table growth.

```
                          1-Second Raw Telemetry Tick
       ┌───────────────────────────────────────────────────────────────┐
       │                 DemoMesh Microservice Simulator               │
       │   (api-gateway, auth, order, payment, inventory, db, redis)   │
       └───────────────────────────────┬───────────────────────────────┘
                                       │ 10 Golden Signals
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │               ContinuousObservabilityCollector                │
       │          (backend/app/services/observability/collector.py)    │
       │  - Polling interval: 5 seconds                                │
       │  - In-memory Accumulators: (service, metric, bucket_minute)   │
       │  - Computes: min, max, average, latest_value, sample_count    │
       └───────────────────────────────┬───────────────────────────────┘
                                       │
                      Flush every 30s or on-demand
                                       │
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │             Database Persistence: `metric_rollups`            │
       │  - Multi-column Index: (service_name, metric_name, bucket)    │
       │  - Duplicate Prevention via upsert merge logic                │
       │  - Rolling 7-Day Pruning (Audit & Incidents Protected)        │
       └───────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
       ┌───────────────────────────────────────────────────────────────┐
       │                 FastAPI Telemetry Endpoints                   │
       │  • GET /api/v1/telemetry/signals (Live 10-signal snapshot)    │
       │  • GET /api/v1/telemetry/metrics/history (Paginated rollups)  │
       │  • GET /api/v1/telemetry/collector/status (Health/Diagnostics)│
       └───────────────────────────────────────────────────────────────┘
```

---

### 2. The 10 Golden Reliability Signals

Each of the 7 microservices produces point-in-time measurements across 10 critical reliability dimensions:

| Signal # | Metric Identifier | Canonical Unit | Typical Range | SRE Significance |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `cpu_utilization` | Percent (%) | 0.0 – 100.0% | Detects compute saturation and runaway thread loops. |
| **2** | `memory_utilization` | Percent (%) | 0.0 – 100.0% | Detects progressive leaks, heap saturation, and OOM risk. |
| **3** | `disk_utilization` | Percent (%) | 0.0 – 100.0% | Monitors storage exhaustion and database WAL/data growth. |
| **4** | `network_throughput_mbps` | Megabytes / sec (MB/s) | $\ge 0.0$ | Identifies network saturation, egress spikes, and socket drops. |
| **5** | `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms` | Milliseconds (ms) | $> 0.0$ | Golden signal for user-perceived performance and tail degradation. |
| **6** | `error_rate` | Percent (%) | 0.0 – 100.0% | HTTP 5xx and connection failure rate against nominal thresholds. |
| **7** | `db_pool_utilization` | Percent (%) | 0.0 – 100.0% | Measures database connection acquisition and starvation risk. |
| **8** | `availability_pct` | Percent (%) | 0.0 – 100.0% | SLI availability baseline (99.9% nominal; drops on degradation). |
| **9** | `dependency_health` | Score / % | 0.0 – 100.0% | Composite health score of outbound downstream dependency topology. |
| **10** | `request_rate` | Requests / sec (RPS) | $\ge 0.0$ | System throughput and demand volume across cluster gateways. |

> [!NOTE]
> **Data Source Attribution:** Every emitted signal and historical rollup carries an explicit `data_source` tag (`SIMULATED`, `LIVE`, or `REPLAY`). Simulated data is strictly segregated from live production measurements.

---

### 3. Database Models & Schema Foundations

#### A. `MetricRollup` Table (`metric_rollups`)
Downsampled 1-minute time-bucket rollup:
- `id`: String(36) UUID primary key
- `service_id`: String(36) Foreign Key (`services.id`, nullable, indexed)
- `service_name`: String(100) indexed
- `metric_name`: String(100) indexed
- `bucket_start`: DateTime(timezone=True) indexed (rounded to minute boundary)
- `minimum`: Float
- `maximum`: Float
- `average`: Float
- `latest_value`: Float
- `sample_count`: Integer
- `data_source`: String(20) (`SIMULATED` by default)
- `created_at`: DateTime(timezone=True)
- `UniqueConstraint("service_name", "metric_name", "bucket_start")`

#### B. Future Phase 5 Foundations (Zero-Code Schema Shells)
Created to ensure future stages build upon established schemas without migration downtime:
- `slo_definitions`: Configurable service-level objectives (`service_id`, `slo_type`, `target_percentage`, `window_days`, `threshold_value`, `is_active`).
- `slo_measurements`: Calculated error budget snapshots (`current_sli`, `error_budget_remaining`, `burn_rate`).
- `anomaly_records`: Persisted anomaly events with deviation, confidence, and supporting evidence.
- `regression_records`: Recurring incident detection comparing baseline, post-remediation, and current metric states.
- `predictive_warnings`: Proactive alerts for projected resource exhaustion ($TTE$) and creep.

---

### 4. Background Collector Mechanics

The [`ContinuousObservabilityCollector`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/backend/app/services/observability/collector.py) operates as a non-blocking background task:

1. **Sampling & Accumulation:**
   - Samples `DemoMesh` every 5 seconds.
   - Groups metrics into 1-minute buckets: `bucket_start = dt.replace(second=0, microsecond=0)`.
   - Aggregates min, max, sum, and count in memory using `MetricBucketAccumulator`.
2. **Persistence & Deduplication:**
   - Completed buckets are flushed every 30 seconds or on-demand via `POST /api/v1/telemetry/collector/flush`.
   - Duplicate writes for identical `(service_name, metric_name, bucket_start)` are merged idempotently into existing rows without primary key collisions.
3. **Storage Optimization & 7-Day Retention:**
   - Pruning query: `DELETE FROM metric_rollups WHERE bucket_start < (now - 7 days)`.
   - Runs automatically once per hour or on-demand.
   - **Protection Invariant:** Explicitly isolates metric rollups; audit logs, incidents, and investigation evidence are strictly protected from pruning.
4. **Lifecycle & Startup:**
   - Integrated into FastAPI `lifespan` in `backend/main.py`.
   - Starts asynchronously after DB connection verification; stops cleanly on SIGTERM/SIGINT.

---

### 5. API Endpoints

#### 1. Latest 10 Golden Signals
`GET /api/v1/telemetry/signals`
```json
{
  "timestamp": "2026-11-11T04:34:01.926555Z",
  "data_source": "SIMULATED",
  "total_services": 7,
  "services": {
    "order-service": {
      "service_id": "e807c9f6-ea2b-426c-89bb-d63a08dca858",
      "service_name": "order-service",
      "cpu_utilization": 29.42,
      "memory_utilization": 51.62,
      "disk_utilization": 37.62,
      "network_throughput_mbps": 8.79,
      "latency_p50_ms": 44.05,
      "latency_p95_ms": 100.56,
      "latency_p99_ms": 171.18,
      "error_rate": 0.22,
      "db_pool_utilization": 17.87,
      "availability_pct": 99.9,
      "dependency_health": 100.0,
      "request_rate": 13.44,
      "health_status": "HEALTHY",
      "data_source": "SIMULATED"
    }
  }
}
```

#### 2. Historical Metric Rollups
`GET /api/v1/telemetry/metrics/history?service_name=order-service&metric_name=cpu_utilization&page=1&page_size=2`
```json
{
  "total": 60,
  "page": 1,
  "page_size": 2,
  "total_pages": 30,
  "data_source": "SIMULATED",
  "rollups": [
    {
      "id": "3c834fa6-6c4b-4820-8aa0-34bb25b6b3e1",
      "service_id": "e807c9f6-ea2b-426c-89bb-d63a08dca858",
      "service_name": "order-service",
      "metric_name": "cpu_utilization",
      "bucket_start": "2026-11-11T04:34:00Z",
      "minimum": 25.12,
      "maximum": 33.45,
      "average": 28.67,
      "latest_value": 29.42,
      "sample_count": 12,
      "data_source": "SIMULATED"
    }
  ]
}
```

#### 3. Collector Operational Health
`GET /api/v1/telemetry/collector/status`
```json
{
  "collector_status": "RUNNING",
  "last_collection_time": "2026-11-11T04:34:50.335342Z",
  "last_flush_time": "2026-11-11T04:34:20.326234Z",
  "last_cleanup_time": null,
  "next_collection_interval_seconds": 5,
  "monitored_services_count": 7,
  "buffer_stats": {
    "active_buckets_in_memory": 84,
    "total_samples_collected": 1008,
    "total_rollups_persisted": 84
  },
  "last_error": null
}
```

---

### 6. Automated Testing Verification

The test suite [`tests/backend/test_stage_5_1_observability.py`](file:///Users/kmprabhu/.gemini/antigravity/scratch/incidentx-ai/tests/backend/test_stage_5_1_observability.py) exercises all 16 required test scenarios:
- **Test 1:** 10 Golden Signals generated with valid bounds.
- **Test 2:** All 7 microservices present in telemetry payload.
- **Test 3:** Accurate statistical aggregation (min, max, avg, latest, count).
- **Test 4:** Proper 1-minute bucket boundary truncation.
- **Test 5:** Rollup database persistence to `metric_rollups`.
- **Test 6:** Duplicate rollup deduplication and merging.
- **Test 7:** Robust handling of invalid data (`None`, `NaN`, `Inf`).
- **Test 8:** Safe recovery from missing telemetry keys.
- **Test 9:** Strict data source attribution (`SIMULATED`, `LIVE`).
- **Test 10:** Historical query filtering by service, metric, time window.
- **Test 11:** Pagination enforcement and bounds limits.
- **Test 12:** 7-day retention pruning of aged records.
- **Test 13:** Retention protection for audit logs and incident records.
- **Test 14:** Non-blocking collector startup and shutdown.
- **Test 15:** Collector resiliency under transient database errors.
- **Test 16:** Collector status endpoint reporting.

**Verification Results:**
- Stage 5.1 Pytest Suite: **16 / 16 passed in 0.10s**
- Full System Pytest Suite: **58 / 58 passed in 1.19s** (42 Phase 0–4 + 16 Stage 5.1)
- Live System Integration Suite: **25 / 25 checks passed** (`scripts/test_integration.py`)

---

### 7. Known Limitations & Next Steps

1. **Resolution:** Stage 5.1 persists downsampled 1-minute rollups; sub-second raw measurements remain in high-speed ring buffers (300s window) for real-time Prometheus scraping.
2. **Next Stage (Stage 5.2 & 5.3):**
   - Stage 5.2: Metric collection enhancement and persistent historical storage indexing.
   - Stage 5.3: Intelligent Anomaly Detection Engine (EWMA filters, linear slope regression for slow memory/connection pool leaks, and confidence scoring).
