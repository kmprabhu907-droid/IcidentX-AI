"""
INCIDENTX AI - Observability API Endpoints
Provides cluster-wide health overview, service health states, recent anomaly alerts,
advanced resource-creep detections, dynamic baselines, and lifecycle status management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query
from backend.app.services.observability.anomaly import anomaly_service
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
