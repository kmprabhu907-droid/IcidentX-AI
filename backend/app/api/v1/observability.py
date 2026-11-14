"""
INCIDENTX AI - Observability API Endpoints
Provides cluster-wide health overview, service health states, recent anomaly alerts,
advanced resource-creep detections, dynamic baselines, and lifecycle status management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.services.observability.anomaly import anomaly_service
from backend.app.services.observability.engine import observability_engine
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.regression import RegressionLifecycleService
from backend.app.services.observability.prometheus import prometheus_client, promql_library
from backend.app.services.observability.opentelemetry import otel_collector, trace_investigator
from backend.app.services.observability.grafana import grafana_client
from backend.app.services.observability.unified_correlation_engine import unified_correlation_engine
from backend.app.services.observability.telemetry_anomaly_engine import telemetry_anomaly_engine

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/overview")
async def get_cluster_overview() -> Dict[str, Any]:
    """Retrieve high-level cluster health, throughput, error rate, and anomaly count."""
    return observability_engine.get_cluster_overview()


@router.get("/alerts")
async def list_recent_alerts(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """List recent anomaly detection alerts from the 5 detector modules."""
    return observability_engine.get_recent_alerts(limit=limit)


@router.get("/anomalies")
async def list_anomalies(
    service_name: Optional[str] = Query(None, description="Filter by affected microservice name"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    severity: Optional[str] = Query(None, description="Filter by severity (INFO, LOW, MEDIUM, HIGH, CRITICAL)"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)"),
    start_time: Optional[datetime] = Query(None, description="Filter detections on or after timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter detections on or before timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
) -> Dict[str, Any]:
    """
    Stage 5.2: Query historical and active anomaly records with multi-attribute filtering
    and pagination.
    """
    return await anomaly_service.list_anomalies(
        service_name=service_name,
        metric_name=metric_name,
        severity=severity,
        status=status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.get("/anomalies/active")
async def get_active_anomalies() -> List[Dict[str, Any]]:
    """
    Stage 5.2: Returns all currently ACTIVE or ACKNOWLEDGED anomalies across the topology.
    """
    return await anomaly_service.get_active_anomalies()


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly_details(anomaly_id: str) -> Dict[str, Any]:
    """
    Stage 5.2: Retrieve full explainable diagnostic breakdown answering the 10 SRE questions
    for a specific anomaly by UUID.
    """
    rec = await anomaly_service.get_anomaly_by_id(anomaly_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Anomaly record '{anomaly_id}' not found.")
    return rec


@router.patch("/anomalies/{anomaly_id}/status")
async def update_anomaly_status(
    anomaly_id: str,
    status: str = Body(..., embed=True, description="New status: ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE"),
) -> Dict[str, Any]:
    """
    Stage 5.2: Update the lifecycle status of an anomaly record.
    """
    try:
        updated = await anomaly_service.update_anomaly_status(anomaly_id, status)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Anomaly record '{anomaly_id}' not found.")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/detection/status")
async def get_detection_status() -> Dict[str, Any]:
    """
    Stage 5.2: Health, cycle status, total anomaly counts, and active detector diagnostics.
    """
    return anomaly_service.get_status()


@router.post("/detection/trigger")
async def trigger_detection_cycle() -> Dict[str, Any]:
    """
    Stage 5.2: Manually trigger an immediate anomaly detection cycle.
    """
    results = await anomaly_service.run_detection_cycle()
    return {
        "status": "COMPLETED",
        "timestamp": datetime.now().isoformat(),
        "candidates_detected_count": len(results),
        "candidates": results,
    }


@router.get("/baselines/{service_id}")
async def get_service_baselines(service_id: str) -> Dict[str, Any]:
    """
    Stage 5.2: Inspect dynamic baseline mean, variance, and normal operating bands
    for all 10 Golden Signals for a given service.
    """
    return anomaly_service.get_service_baselines(service_id)


@router.get("/services")
async def list_service_telemetry() -> Dict[str, Any]:
    """List all demo microservices with their current real-time telemetry snapshot."""
    latest = demo_mesh.get_latest_metrics()
    is_simulated = len(demo_mesh.active_faults) > 0 or any(
        s.get("data_source") == "SIMULATED" for s in latest.values()
    )
    return {
        "services": latest,
        "data_source": "SIMULATED" if is_simulated else "LIVE",
    }


@router.get("/services/{service_name}/metrics")
async def get_service_metrics(
    service_name: str,
    seconds: int = Query(60, ge=10, le=300)
) -> Dict[str, Any]:
    """Retrieve chronological 1-second resolution metrics history for a specific service."""
    history = demo_mesh.get_service_history(service_name, seconds=seconds)
    return {
        "service_name": service_name,
        "seconds": seconds,
        "data_source": "SIMULATED" if len(demo_mesh.active_faults) > 0 else "LIVE",
        "history": history,
    }


# =========================================================================
# Stage 5.3: Regression Detection Lab & Historical Failure Intelligence
# =========================================================================

@router.get("/regressions")
async def list_regressions(
    service_name: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Query regression records with filtering, classification, and pagination.
    """
    return await RegressionLifecycleService.list_regressions(
        db=db,
        service_name=service_name,
        metric_name=metric_name,
        status=status,
        classification=classification,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )


@router.get("/regressions/active")
async def get_active_regressions(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Stage 5.3: Return currently active or investigating regressions across the cluster.
    """
    return await RegressionLifecycleService.get_active_regressions(db)


@router.get("/regressions/{regression_id}")
async def get_regression_by_id(
    regression_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Retrieve full regression record with 10 SRE diagnostic answers.
    """
    record = await RegressionLifecycleService.get_regression_by_id(regression_id, db)
    if not record:
        raise HTTPException(status_code=404, detail=f"Regression record '{regression_id}' not found.")
    return record


@router.patch("/regressions/{regression_id}/status")
async def update_regression_status(
    regression_id: str,
    status: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Transition regression lifecycle status (ACTIVE, INVESTIGATING, CONFIRMED, RESOLVED, FALSE_POSITIVE).
    """
    try:
        updated = await RegressionLifecycleService.update_status(regression_id, status, db)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Regression record '{regression_id}' not found.")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/regressions/{regression_id}/comparison")
async def get_regression_comparison(
    regression_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Four-state comparison matrix (Healthy Baseline, Pre-Incident, Post-Remediation, Current State).
    """
    comp = await RegressionLifecycleService.get_comparison(regression_id, db)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Four-state comparison for '{regression_id}' not found.")
    return comp


@router.get("/regressions/{regression_id}/history")
async def get_regression_history(
    regression_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Historical incident provenance, past remediation actions, and recurrence timeline.
    """
    return await RegressionLifecycleService.get_history(regression_id, db)


@router.get("/remediation-effectiveness")
async def get_remediation_effectiveness(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Cluster-wide overview of Phase 4 remediation stability and long-term outcomes.
    """
    return await RegressionLifecycleService.get_remediation_effectiveness_overview(db)


@router.post("/regressions/trigger")
async def trigger_regression_detection(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Stage 5.3: Trigger manual cluster regression evaluation.
    """
    evaluated = await RegressionLifecycleService.evaluate_and_record_regressions(db)
    return {
        "status": "COMPLETED",
        "timestamp": datetime.now().isoformat(),
        "evaluated_records_count": len(evaluated),
        "records": [RegressionLifecycleService._format_record(r) for r in evaluated],
    }


# =========================================================================
# Phase 8.3: Live Observability Endpoints (Prometheus, OpenTelemetry, Grafana)
# =========================================================================

@router.get("/status")
async def get_observability_status() -> Dict[str, Any]:
    """
    Phase 8.3: Retrieve overall live health, metrics, trace ingestion and Grafana status.
    """
    prom_health = await prometheus_client.check_health()
    graf_health = await grafana_client.check_health()
    overall = (
        "HEALTHY"
        if prom_health.status in ("AVAILABLE", "NOT_CONFIGURED") and graf_health.get("status") in ("AVAILABLE", "NOT_CONFIGURED")
        else "DEGRADED"
    )
    return {
        "status": overall,
        "prometheus": prom_health.model_dump(),
        "opentelemetry": {
            "status": "AVAILABLE" if otel_collector.total_ingested_spans > 0 or getattr(settings, "OTEL_ENABLED", True) else "NOT_CONFIGURED",
            "buffered_traces_count": len(otel_collector._traces),
            "total_ingested_spans": otel_collector.total_ingested_spans,
            "total_ingested_traces": otel_collector.total_ingested_traces,
        },
        "grafana": graf_health,
        "active_environment_mode": environment_manager.current_mode.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/prometheus/health")
async def get_prometheus_health() -> Dict[str, Any]:
    """
    Phase 8.3: Connection health check against Prometheus /-/healthy.
    """
    health = await prometheus_client.check_health()
    return health.model_dump()


@router.get("/metrics")
async def list_available_metrics(
    metric: Optional[str] = Query(None, description="Filter by metric name substring")
) -> Dict[str, Any]:
    """
    Phase 8.3: Discover available metrics and type metadata from Prometheus.
    """
    metadata = await prometheus_client.get_metadata(metric=metric)
    return {
        "count": len(metadata),
        "metrics": [m.model_dump() for m in metadata],
    }


@router.get("/metrics/catalog")
async def get_metrics_catalog(
    category: Optional[str] = Query(None, description="Optional category filter: CONTAINER, APPLICATION, NETWORK, KUBERNETES, NODE")
) -> Dict[str, Any]:
    """
    Phase 8.3: Predefined PromQL Query Library with parameterization and unit specifications.
    """
    templates = promql_library.list_templates(category=category)
    return {
        "count": len(templates),
        "catalog": [t.model_dump() for t in templates],
    }


@router.get("/metrics/query")
async def execute_instant_metric_query(
    query: str = Query(..., description="PromQL expression or template query"),
    time: Optional[str] = Query(None, description="Evaluation timestamp (RFC3339 or unix seconds)")
) -> Dict[str, Any]:
    """
    Phase 8.3: Execute instant PromQL query with safe division and missing-metric resilience.
    """
    result = await prometheus_client.query(promql=query, time_param=time)
    return result.model_dump()


@router.get("/metrics/query_range")
async def execute_range_metric_query(
    query: str = Query(..., description="PromQL expression"),
    start: str = Query(..., description="Start timestamp"),
    end: str = Query(..., description="End timestamp"),
    step: str = Query("15s", description="Query resolution step (e.g. 15s, 1m)")
) -> Dict[str, Any]:
    """
    Phase 8.3: Execute range PromQL query.
    """
    result = await prometheus_client.query_range(promql=query, start=start, end=end, step=step)
    return result.model_dump()


@router.get("/traces")
async def list_traces(
    service_name: Optional[str] = Query(None, description="Filter by root or participating service name"),
    only_errors: bool = Query(False, description="Filter to only traces with error spans"),
    incident_id: Optional[str] = Query(None, description="Filter by linked incident ID"),
    min_duration_ms: Optional[float] = Query(None, description="Filter by minimum span duration"),
    limit: int = Query(50, ge=1, le=200, description="Max traces to return"),
) -> Dict[str, Any]:
    """
    Phase 8.3: Retrieve buffered OpenTelemetry traces.
    """
    traces = otel_collector.list_traces(
        service_name=service_name,
        only_errors=only_errors,
        incident_id=incident_id,
        min_duration_ms=min_duration_ms,
        limit=limit,
    )
    return {
        "count": len(traces),
        "traces": [t.model_dump() for t in traces],
    }


@router.get("/traces/{trace_id}")
async def get_trace_detail(trace_id: str) -> Dict[str, Any]:
    """
    Phase 8.3: Retrieve detailed OpenTelemetry trace waterfall, bottleneck identification,
    and caller-callee dependency edges.
    """
    trace = otel_collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found in active buffer.")
    return trace_investigator.analyze_trace(trace)


@router.post("/traces/ingest")
async def ingest_opentelemetry_traces(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Phase 8.3: Ingest standard OTLP HTTP/JSON trace payload with resourceSpans, scopeSpans, and spans.
    """
    ingested_ids = otel_collector.ingest_otlp_payload(payload)
    return {
        "status": "INGESTED",
        "ingested_count": len(ingested_ids),
        "trace_ids": ingested_ids,
    }


@router.get("/timeline/{incident_id}")
async def get_correlated_incident_timeline(
    incident_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Phase 8.3: Synthesize unified correlation timeline for an incident across
    Prometheus metrics, OTel traces, K8s events, application logs, and incident states.
    """
    timeline = await unified_correlation_engine.build_incident_timeline(
        incident_id=incident_id,
        session=db,
        limit=limit,
    )
    return {
        "incident_id": incident_id,
        "count": len(timeline),
        "timeline": [item.model_dump() for item in timeline],
    }


@router.get("/grafana/dashboards")
async def search_grafana_dashboards(query: str = Query("", description="Dashboard title search query")) -> List[Dict[str, Any]]:
    """
    Phase 8.3: Search available Grafana dashboards.
    """
    dashboards = await grafana_client.search_dashboards(query=query)
    return [d.model_dump() for d in dashboards]


@router.get("/grafana/deep-link")
async def get_grafana_deep_link(
    dashboard_uid: Optional[str] = Query(None),
    from_time_ms: Optional[int] = Query(None),
    to_time_ms: Optional[int] = Query(None),
    namespace: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    incident_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Phase 8.3: Generate scoped Grafana deep-link without exposing backend API credentials.
    """
    url = grafana_client.generate_incident_deep_link(
        dashboard_uid=dashboard_uid,
        from_time_ms=from_time_ms,
        to_time_ms=to_time_ms,
        namespace=namespace,
        service=service,
        incident_id=incident_id,
    )
    return {"url": url}


@router.post("/grafana/annotations")
async def create_grafana_annotation(
    payload: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Phase 8.3: Post incident lifecycle annotation to Grafana dashboard.
    """
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Annotation text is required.")
    ann = await grafana_client.create_annotation(
        text=text,
        tags=payload.get("tags"),
        dashboard_uid=payload.get("dashboard_uid"),
        time_ms=payload.get("time_ms"),
        time_end_ms=payload.get("time_end_ms"),
    )
    if not ann:
        return {"status": "SKIPPED", "message": "Grafana annotation was not created (disabled or unreachable)."}
    return {"status": "CREATED", "annotation": ann.model_dump()}


@router.get("/anomalies/explainable")
async def list_explainable_anomalies(
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Phase 8.3: List confirmed explainable anomalies from the TelemetryAnomalyEngine.
    """
    anomalies = telemetry_anomaly_engine.list_recent_anomalies(limit=limit)
    return {
        "count": len(anomalies),
        "anomalies": [a.model_dump() for a in anomalies],
    }


@router.post("/anomalies/evaluate")
async def evaluate_metric_anomaly(
    resource_name: str = Body(...),
    metric_name: str = Body(...),
    current_value: float = Body(...),
    data_source: str = Body("PROMETHEUS"),
) -> Dict[str, Any]:
    """
    Phase 8.3: Evaluate an incoming metric data point against the explainable anomaly engine.
    """
    rec = telemetry_anomaly_engine.evaluate_metric(
        resource_name=resource_name,
        metric_name=metric_name,
        current_value=current_value,
        data_source=data_source,
    )
    if rec:
        return {"anomaly_detected": True, "record": rec.model_dump()}
    return {"anomaly_detected": False, "message": "Sample within expected baseline or consecutive breach threshold not met."}

