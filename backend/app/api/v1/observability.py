"""
INCIDENTX AI - Observability API Endpoints
Provides cluster-wide health overview, service health states, and recent anomaly alerts.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from backend.app.services.observability.engine import observability_engine
from backend.app.services.observability.demo_mesh import demo_mesh

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/overview")
async def get_cluster_overview() -> Dict[str, Any]:
    """Retrieve high-level cluster health, throughput, error rate, and anomaly count."""
    return observability_engine.get_cluster_overview()


@router.get("/alerts")
async def list_recent_alerts(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """List recent anomaly detection alerts from the 5 detector modules."""
    return observability_engine.get_recent_alerts(limit=limit)


@router.get("/services")
async def list_service_telemetry() -> Dict[str, Any]:
    """List all demo microservices with their current real-time telemetry snapshot."""
    latest = demo_mesh.get_latest_metrics()
    is_simulated = len(demo_mesh.active_faults) > 0
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
