"""
INCIDENTX AI - Phase 8.3 Live Observability Test Suite
Tests Prometheus integration, PromQL library, OpenTelemetry trace ingestion,
Trace investigation & bottleneck detection, Grafana deep-linking, Unified Telemetry correlation,
Explainable anomaly detection, and FastAPI endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.app.core.config import settings
from backend.app.infrastructure.core.infrastructure_models import (
    OpenTelemetrySpan,
    OpenTelemetryTrace,
    PrometheusQueryResult,
)
from backend.app.services.observability.prometheus import (
    PrometheusClient,
    prometheus_client,
    promql_library,
)
from backend.app.services.observability.opentelemetry import (
    OpenTelemetryCollector,
    otel_collector,
    trace_investigator,
)
from backend.app.services.observability.grafana import (
    GrafanaClient,
    grafana_client,
)
from backend.app.services.observability.unified_correlation_engine import (
    unified_correlation_engine,
)
from backend.app.services.observability.telemetry_anomaly_engine import (
    TelemetryAnomalyEngine,
    telemetry_anomaly_engine,
)
from backend.app.services.investigation.agents.trace_agent import TraceAnalysisAgent


# =========================================================================
# 1. Prometheus Client & PromQL Library Tests
# =========================================================================

@pytest.mark.asyncio
async def test_prometheus_unreachable_endpoint_handling():
    """Verify Prometheus client reports honest UNAVAILABLE status when port is unreachable."""
    client = PrometheusClient(base_url="http://127.0.0.1:59999", timeout_seconds=0.5)
    health = await client.check_health()
    assert health.status in ("UNAVAILABLE", "ERROR")
    assert health.latency_ms >= 0.0

    res = await client.query("up")
    assert res.status == "UNAVAILABLE"
    assert "Unable to connect" in res.error_message or "timed out" in res.error_message


@pytest.mark.asyncio
async def test_prometheus_sandbox_query_parsing():
    """Verify PromQL instant and range query JSON envelope parsing."""
    client = PrometheusClient()

    def mock_handler(action, params):
        if action == "query":
            return {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {"__name__": "http_requests_total", "service": "order-service"},
                            "value": [1731348000.123, "142.5"],
                        }
                    ],
                },
            }
        elif action == "query_range":
            return {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"__name__": "container_cpu_usage_seconds_total", "pod": "order-pod-1"},
                            "values": [
                                [1731348000, "0.45"],
                                [1731348015, "0.55"],
                            ],
                        }
                    ],
                },
            }
        return {"status": "error", "error": "unknown action"}

    client.set_mock_sandbox_handler(mock_handler)

    # Instant vector query
    vec_res = await client.query("http_requests_total")
    assert vec_res.status == "SUCCESS"
    assert len(vec_res.series) == 1
    assert vec_res.series[0].latest_value == 142.5
    assert vec_res.series[0].labels["service"] == "order-service"

    # Range matrix query
    mat_res = await client.query_range("container_cpu_usage_seconds_total", start="0", end="30")
    assert mat_res.status == "SUCCESS"
    assert len(mat_res.series) == 1
    assert mat_res.series[0].latest_value == 0.55
    assert len(mat_res.series[0].values) == 2


def test_promql_library_templates_and_safe_clamp():
    """Verify PromQL templates have clamp_min to avoid zero division and render correctly."""
    templates = promql_library.list_templates()
    assert len(templates) >= 10

    # Verify safe denominator in error rate query
    err_template = promql_library.get_template("http_error_rate_percent")
    assert err_template is not None
    assert "clamp_min" in err_template.query_template

    # Verify rendering
    rendered = promql_library.render_query(
        "http_error_rate_percent",
        service="checkout-service",
    )
    assert 'service=~"checkout-service"' in rendered


# =========================================================================
# 2. OpenTelemetry Trace Ingestion & Investigation Engine Tests
# =========================================================================

def test_opentelemetry_otlp_json_ingestion():
    """Verify parsing OTLP HTTP/JSON payload with resource and scope spans."""
    collector = OpenTelemetryCollector(max_buffer_size=10)

    otlp_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "payment-service"}},
                        {"key": "k8s.pod.name", "value": {"stringValue": "payment-pod-xyz"}},
                        {"key": "k8s.namespace.name", "value": {"stringValue": "prod"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "trace-otlp-1",
                                "spanId": "span-1",
                                "name": "POST /charge",
                                "startTimeUnixNano": "1731348000000000000",
                                "endTimeUnixNano": "1731348001200000000",
                                "status": {"code": 1},
                            },
                            {
                                "traceId": "trace-otlp-1",
                                "spanId": "span-2",
                                "parentSpanId": "span-1",
                                "name": "stripe.charge",
                                "startTimeUnixNano": "1731348000100000000",
                                "endTimeUnixNano": "1731348001150000000",
                                "status": {"code": 2, "message": "Gateway timeout 504"},
                            },
                        ]
                    }
                ],
            }
        ]
    }

    ingested = collector.ingest_otlp_payload(otlp_payload)
    assert "trace-otlp-1" in ingested

    trace = collector.get_trace("trace-otlp-1")
    assert trace is not None
    assert trace.span_count == 2
    assert trace.has_error is True
    assert trace.error_count == 1
    assert trace.root_service == "payment-service"
    assert trace.duration_ms == 1200.0


def test_trace_investigator_bottleneck_and_hierarchy():
    """Verify trace analysis identifies bottleneck spans, error spans, and depth tree."""
    trace = OpenTelemetryTrace(
        trace_id="trace-bench-1",
        root_service="gateway",
        root_operation="GET /items",
        start_time_iso="2026-11-11T12:00:00Z",
        duration_ms=850.0,
        span_count=3,
        error_count=1,
        has_error=True,
        spans=[
            OpenTelemetrySpan(
                trace_id="trace-bench-1",
                span_id="s1",
                parent_span_id=None,
                name="GET /items",
                service_name="gateway",
                start_time_iso="2026-11-11T12:00:00Z",
                end_time_iso="2026-11-11T12:00:00.850Z",
                duration_ms=850.0,
                status_code="OK",
            ),
            OpenTelemetrySpan(
                trace_id="trace-bench-1",
                span_id="s2",
                parent_span_id="s1",
                name="query_items",
                service_name="inventory-service",
                start_time_iso="2026-11-11T12:00:00.050Z",
                end_time_iso="2026-11-11T12:00:00.800Z",
                duration_ms=750.0,
                status_code="ERROR",
                status_message="Database lock timeout",
                is_error=True,
            ),
            OpenTelemetrySpan(
                trace_id="trace-bench-1",
                span_id="s3",
                parent_span_id="s2",
                name="SELECT * FROM items",
                service_name="postgres",
                start_time_iso="2026-11-11T12:00:00.060Z",
                end_time_iso="2026-11-11T12:00:00.780Z",
                duration_ms=720.0,
                status_code="ERROR",
                is_error=True,
            ),
        ],
    )

    analysis = trace_investigator.analyze_trace(trace)
    assert analysis["has_error"] is True
    assert analysis["bottleneck_span"]["span_id"] == "s1"
    assert len(analysis["error_spans"]) == 2

    # Check tree hierarchy depth
    tree = analysis["tree"]
    assert len(tree) == 3
    assert tree[0]["depth"] == 0  # s1 root
    assert tree[1]["depth"] == 1  # s2 child of s1
    assert tree[2]["depth"] == 2  # s3 child of s2

    # Check caller -> callee dependency edges
    edges = analysis["dependency_edges"]
    assert any(e["source_service"] == "gateway" and e["target_service"] == "inventory-service" for e in edges)
    assert any(e["source_service"] == "inventory-service" and e["target_service"] == "postgres" for e in edges)


# =========================================================================
# 3. Grafana Client Tests
# =========================================================================

def test_grafana_deep_link_generation_without_secret_leak():
    """Verify deep-link generator constructs URL with time-range and template variables without token."""
    client = GrafanaClient(base_url="https://grafana.internal.net", api_key="SUPER_SECRET_TOKEN_DO_NOT_LEAK")
    url = client.generate_incident_deep_link(
        dashboard_uid="k8s-pod-overview",
        from_time_ms=1731340000000,
        to_time_ms=1731343600000,
        namespace="production",
        service="order-service",
        incident_id="INC-99",
    )
    assert "https://grafana.internal.net/d/k8s-pod-overview/incident-view" in url
    assert "from=1731340000000" in url
    assert "to=1731343600000" in url
    assert "var-namespace=production" in url
    assert "var-service=order-service" in url
    assert "var-incident=INC-99" in url
    # Verify SECRET KEY is NOT exposed in the URL!
    assert "SUPER_SECRET_TOKEN_DO_NOT_LEAK" not in url


@pytest.mark.asyncio
async def test_grafana_mock_sandbox_annotations():
    """Verify annotation creation against Grafana sandbox handler."""
    client = GrafanaClient()

    def mock_handler(action, payload):
        if action == "create_annotation":
            return {"id": 42}
        return {}

    client.set_mock_sandbox_handler(mock_handler)
    ann = await client.create_annotation(text="Incident INC-101 Mitigated", tags=["mitigation", "incidentx"])
    assert ann is not None
    assert ann.id == 42
    assert "incidentx" in ann.tags
    assert ann.text == "Incident INC-101 Mitigated"


# =========================================================================
# 4. Explainable Anomaly Detection Engine Tests
# =========================================================================

def test_anomaly_detection_consecutive_breaches_anti_flapping():
    """Verify anomaly detection requires 3 consecutive breaches before firing alert."""
    detector = TelemetryAnomalyEngine(consecutive_breaches_required=3)

    # Sample 1: breach (CPU 95% > 80%) -> should NOT trigger yet
    r1 = detector.evaluate_metric("pod-auth", "cpu_utilization", 95.0)
    assert r1 is None

    # Sample 2: breach (CPU 94% > 80%) -> should NOT trigger yet
    r2 = detector.evaluate_metric("pod-auth", "cpu_utilization", 94.0)
    assert r2 is None

    # Sample 3: breach (CPU 96% > 80%) -> SHOULD trigger confirmed anomaly!
    r3 = detector.evaluate_metric("pod-auth", "cpu_utilization", 96.0)
    assert r3 is not None
    assert r3.consecutive_breaches == 3
    assert r3.detector_type == "STATIC_THRESHOLD"
    assert "breached static threshold" in r3.explanation

    # Sample 4: normal sample (CPU 40%) -> resets consecutive counter
    r4 = detector.evaluate_metric("pod-auth", "cpu_utilization", 40.0)
    assert r4 is None
    tracker = detector._get_tracker("pod-auth", "cpu_utilization")
    assert tracker.consecutive_count == 0


def test_anomaly_detection_rolling_z_score():
    """Verify rolling baseline Z-score anomaly detection."""
    detector = TelemetryAnomalyEngine(consecutive_breaches_required=1, default_sigma_threshold=3.0)

    # Feed steady baseline values around 20.0
    for _ in range(10):
        detector.evaluate_metric("redis-node", "custom_queue_depth", 20.0)

    # Spike significantly above baseline (100.0)
    spike = detector.evaluate_metric("redis-node", "custom_queue_depth", 100.0)
    assert spike is not None
    assert spike.detector_type == "ROLLING_BASELINE"
    assert spike.deviation_sigma is not None and spike.deviation_sigma > 3.0
    assert "deviated from rolling baseline" in spike.explanation


# =========================================================================
# 5. Unified Telemetry Correlation Engine Tests
# =========================================================================

@pytest.mark.asyncio
async def test_unified_correlation_timeline():
    """Verify unified correlation timeline normalizes UTC timestamps and sorts chronologically."""
    # Ingest a test span into global collector
    otel_collector.clear()
    otel_collector.ingest_otlp_payload({
        "spans": [
            {
                "trace_id": "t-corr-1",
                "span_id": "s-corr-1",
                "name": "db.select",
                "service.name": "order-service",
                "start_time": "2026-11-11T10:00:00Z",
                "end_time": "2026-11-11T10:00:01.200Z",
                "duration_ms": 1200.0,
                "status": "ERROR",
                "incident_id": "INC-CORR-1",
            }
        ]
    })

    timeline = await unified_correlation_engine.build_incident_timeline(incident_id="INC-CORR-1", session=None)
    assert len(timeline) >= 1
    span_item = next((i for i in timeline if i.source == "OPENTELEMETRY"), None)
    assert span_item is not None
    assert span_item.category in ("TRACE_FAILURE", "METRIC_ANOMALY")
    assert span_item.severity in ("HIGH", "CRITICAL")
    assert "2026-11-11" in span_item.timestamp


# =========================================================================
# 6. Investigation Agent Live Trace Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_trace_analysis_agent_live_otel_consumption():
    """Verify TraceAnalysisAgent extracts live OpenTelemetry traces from collector."""
    otel_collector.clear()
    otel_collector.ingest_otlp_payload({
        "spans": [
            {
                "trace_id": "t-agent-test",
                "span_id": "s-agent-fail",
                "name": "checkout.process",
                "service.name": "checkout-svc",
                "start_time": "2026-11-11T14:00:00Z",
                "end_time": "2026-11-11T14:00:02.000Z",
                "duration_ms": 2000.0,
                "status": "ERROR",
                "status_code": 500,
                "incident_id": "INC-AGENT-1",
            }
        ]
    })

    agent = TraceAnalysisAgent()
    state = {}
    result_state = await agent.execute("INC-AGENT-1", state, None)
    traces_result = result_state.get("traces", {})
    assert traces_result.get("failed_traces_count") >= 1
    assert traces_result.get("root_cause_span_service") == "checkout-svc"
    assert len(traces_result.get("slowest_spans", [])) >= 1


# =========================================================================
# 7. FastAPI Observability Endpoints Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_api_v1_observability_endpoints():
    """Test all Phase 8.3 live observability HTTP routes via AsyncClient."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/observability/status
        res_status = await client.get("/api/v1/observability/status")
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert "prometheus" in data_status
        assert "opentelemetry" in data_status
        assert "grafana" in data_status

        # 2. GET /api/v1/observability/prometheus/health
        res_prom_health = await client.get("/api/v1/observability/prometheus/health")
        assert res_prom_health.status_code == 200
        assert "status" in res_prom_health.json()

        # 3. GET /api/v1/observability/metrics/catalog
        res_catalog = await client.get("/api/v1/observability/metrics/catalog")
        assert res_catalog.status_code == 200
        assert res_catalog.json()["count"] >= 10

        # 4. GET /api/v1/observability/traces
        res_traces = await client.get("/api/v1/observability/traces")
        assert res_traces.status_code == 200
        assert "traces" in res_traces.json()

        # 5. POST /api/v1/observability/traces/ingest
        res_ingest = await client.post(
            "/api/v1/observability/traces/ingest",
            json={
                "spans": [
                    {
                        "trace_id": "api-test-trace-1",
                        "span_id": "s-api-1",
                        "name": "GET /api/health",
                        "service.name": "gateway",
                        "start_time": "2026-11-11T12:00:00Z",
                        "end_time": "2026-11-11T12:00:00.050Z",
                        "duration_ms": 50.0,
                    }
                ]
            },
        )
        assert res_ingest.status_code == 200
        assert "api-test-trace-1" in res_ingest.json()["trace_ids"]

        # 6. GET /api/v1/observability/traces/{trace_id}
        res_trace_detail = await client.get("/api/v1/observability/traces/api-test-trace-1")
        assert res_trace_detail.status_code == 200
        assert res_trace_detail.json()["trace_id"] == "api-test-trace-1"

        # 7. GET /api/v1/observability/grafana/deep-link
        res_link = await client.get(
            "/api/v1/observability/grafana/deep-link",
            params={"service": "payment-service", "incident_id": "INC-77"},
        )
        assert res_link.status_code == 200
        assert "url" in res_link.json()
        assert "var-service=payment-service" in res_link.json()["url"]

        # 8. POST /api/v1/observability/anomalies/evaluate
        res_anom = await client.post(
            "/api/v1/observability/anomalies/evaluate",
            json={
                "resource_name": "test-pod-x",
                "metric_name": "cpu_utilization",
                "current_value": 45.0,
            },
        )
        assert res_anom.status_code == 200
        assert res_anom.json()["anomaly_detected"] is False

        # 9. GET /api/v1/observability/timeline/default
        res_tl = await client.get("/api/v1/observability/timeline/default")
        assert res_tl.status_code == 200
        assert "timeline" in res_tl.json()
