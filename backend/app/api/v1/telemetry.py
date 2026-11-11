"""
INCIDENTX AI - Telemetry API Endpoints
Provides OpenTelemetry distributed traces, Prometheus metrics, structured correlated logs,
10 Golden Reliability Signals, and 1-minute historical metric rollups.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.telemetry import MetricRollup
from backend.app.schemas.telemetry import (
    CollectorStatusResponse,
    MetricHistoryResponse,
    MetricRollupResponse,
    ServiceGoldenSignals,
    TenGoldenSignalsResponse,
)
from backend.app.services.observability.collector import observability_collector
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.engine import observability_engine

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/signals", response_model=TenGoldenSignalsResponse)
async def get_ten_golden_signals():
    """
    Module 1 / Phase 5: Retrieve the latest Ten Golden Reliability Signals
    for all 7 microservices in the topology:
    1. CPU utilization (%)
    2. Memory utilization (%)
    3. Disk utilization (%)
    4. Network throughput (MB/s)
    5. Latency (P50, P95, P99 ms)
    6. HTTP error rate (%)
    7. Database connection-pool utilization (%)
    8. Service availability (%)
    9. Dependency health score (%)
    10. Request throughput (RPS)
    """
    latest = demo_mesh.get_latest_metrics()
    is_simulated = len(demo_mesh.active_faults) > 0 or any(
        s.get("data_source") == "SIMULATED" for s in latest.values()
    )
    now = datetime.now(timezone.utc)

    services_data: Dict[str, ServiceGoldenSignals] = {}
    for svc_name, snap in latest.items():
        if snap:
            services_data[svc_name] = ServiceGoldenSignals(
                service_id=snap.get("service_id", ""),
                service_name=svc_name,
                cpu_utilization=snap.get("cpu_utilization", 0.0),
                memory_utilization=snap.get("memory_utilization", 0.0),
                disk_utilization=snap.get("disk_utilization", 0.0),
                network_throughput_mbps=snap.get("network_throughput_mbps", 0.0),
                latency_p50_ms=snap.get("latency_p50_ms", 0.0),
                latency_p95_ms=snap.get("latency_p95_ms", 0.0),
                latency_p99_ms=snap.get("latency_p99_ms", 0.0),
                error_rate=snap.get("error_rate", 0.0),
                db_pool_utilization=snap.get("db_pool_utilization", 0.0),
                availability_pct=snap.get("availability_pct", 100.0),
                dependency_health=snap.get("dependency_health", 100.0),
                request_rate=snap.get("request_rate", 0.0),
                health_status=snap.get("health_status", "HEALTHY"),
                data_source=snap.get("data_source", "SIMULATED"),
            )

    return TenGoldenSignalsResponse(
        timestamp=now,
        data_source="SIMULATED" if is_simulated else "LIVE",
        total_services=len(services_data),
        services=services_data,
    )


@router.get("/metrics/history", response_model=MetricHistoryResponse)
async def get_metrics_history(
    service_id: Optional[str] = Query(None, description="Filter by service UUID"),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp (ISO-8601)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp (ISO-8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page (max 500)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve paginated historical 1-minute metric rollups from the database
    with multi-attribute filtering.
    """
    query = select(MetricRollup)
    conditions = []

    if service_id:
        conditions.append(MetricRollup.service_id == service_id)
    if service_name:
        conditions.append(MetricRollup.service_name == service_name)
    if metric_name:
        conditions.append(MetricRollup.metric_name == metric_name)
    if start_time:
        conditions.append(MetricRollup.bucket_start >= start_time)
    if end_time:
        conditions.append(MetricRollup.bucket_start <= end_time)

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    query = query.order_by(MetricRollup.bucket_start.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    rollups = result.scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return MetricHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        data_source="SIMULATED",
        rollups=[MetricRollupResponse.model_validate(r) for r in rollups],
    )


@router.get("/collector/status", response_model=CollectorStatusResponse)
async def get_collector_status():
    """
    Expose health, buffer status, and collection diagnostics for the background collector.
    """
    return observability_collector.get_status()


@router.post("/collector/flush")
async def trigger_collector_flush():
    """Manually flush all in-memory bucket accumulators to the database."""
    count = await observability_collector.flush_pending_buckets(force_all=True)
    return {"status": "SUCCESS", "flushed_rollups_count": count}


@router.post("/collector/retention-cleanup")
async def trigger_retention_cleanup():
    """Manually trigger 7-day retention cleanup."""
    count = await observability_collector.run_retention_cleanup()
    return {"status": "SUCCESS", "pruned_records_count": count}


@router.get("/prometheus")
async def get_prometheus_metrics():
    """Prometheus scrape exposition endpoint."""
    content = observability_engine.export_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4")


@router.get("/metrics")
async def get_metrics_summary() -> Dict[str, Any]:
    """Retrieve current snapshot of metrics across all services."""
    latest = demo_mesh.get_latest_metrics()
    is_simulated = len(demo_mesh.active_faults) > 0 or any(
        s.get("data_source") == "SIMULATED" for s in latest.values()
    )
    return {
        "data_source": "SIMULATED" if is_simulated else "LIVE",
        "metrics": latest,
    }


@router.get("/traces")
async def list_traces(
    limit: int = Query(50, ge=1, le=200),
    service: Optional[str] = Query(None),
    only_errors: bool = Query(False),
    min_duration_ms: Optional[float] = Query(None),
) -> Dict[str, Any]:
    """Query recent distributed traces with span counts and timing summaries."""
    traces = demo_mesh.get_traces(
        limit=limit,
        service=service,
        only_errors=only_errors,
        min_duration_ms=min_duration_ms,
    )
    is_simulated = len(demo_mesh.active_faults) > 0
    return {
        "total": len(traces),
        "data_source": "SIMULATED" if is_simulated else "LIVE",
        "traces": traces,
    }


@router.get("/traces/{trace_id}")
async def get_trace_details(trace_id: str) -> Dict[str, Any]:
    """Retrieve full distributed trace waterfall details including all child spans and error attributes."""
    trace = demo_mesh.get_trace_by_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found in buffer.")
    return trace


@router.get("/logs")
async def list_logs(
    limit: int = Query(100, ge=1, le=500),
    service: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Query structured logs with correlation identifiers (trace_id, span_id)."""
    logs = demo_mesh.get_logs(
        limit=limit,
        service=service,
        level=level,
        trace_id=trace_id,
        search=search,
    )
    is_simulated = len(demo_mesh.active_faults) > 0
    return {
        "total": len(logs),
        "data_source": "SIMULATED" if is_simulated else "LIVE",
        "logs": logs,
    }
