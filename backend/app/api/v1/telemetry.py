"""
INCIDENTX AI - Telemetry API Endpoints
Provides OpenTelemetry distributed traces, Prometheus metrics, and structured correlated logs.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.engine import observability_engine

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/prometheus")
async def get_prometheus_metrics():
    """Prometheus scrape exposition endpoint."""
    content = observability_engine.export_prometheus_metrics()
    return Response(content=content, media_type="text/plain; version=0.0.4")


@router.get("/metrics")
async def get_metrics_summary() -> Dict[str, Any]:
    """Retrieve current snapshot of metrics across all services."""
    latest = demo_mesh.get_latest_metrics()
    is_simulated = len(demo_mesh.active_faults) > 0
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
