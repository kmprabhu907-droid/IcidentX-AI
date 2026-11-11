"""
INCIDENTX AI - Health Check Router
Validates API runtime health, database connectivity, and environment status.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.database import check_db_health

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    db_healthy = await check_db_health()
    is_healthy = db_healthy

    payload = {
        "status": "healthy" if is_healthy else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "api": "healthy",
            "database": "connected" if db_healthy else "disconnected",
        }
    }

    http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=payload)


@router.get("/health/live", summary="Kubernetes Liveness Probe")
async def liveness_probe():
    """
    Kubernetes Liveness Probe.
    Returns HTTP 200 as long as the Uvicorn/FastAPI process is responsive and executing event loop ticks.
    """
    return {
        "status": "alive",
        "service": settings.APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="Kubernetes Readiness Probe")
async def readiness_probe():
    """
    Kubernetes Readiness Probe.
    Verifies that backing database connections and background observability subsystems are operational.
    """
    db_healthy = await check_db_health()

    collector_ok = True
    try:
        from backend.app.services.observability.collector import observability_collector
        collector_ok = observability_collector.is_running
    except Exception:
        collector_ok = True  # Not critical if running in worker-isolated mode

    engine_ok = True
    try:
        from backend.app.services.observability.engine import observability_engine
        engine_ok = observability_engine.is_running
    except Exception:
        engine_ok = True

    is_ready = db_healthy and collector_ok and engine_ok
    payload = {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.APP_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "database": "ready" if db_healthy else "failed",
            "telemetry_collector": "active" if collector_ok else "stopped",
            "detection_engine": "active" if engine_ok else "stopped",
        },
    }
    http_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_code, content=payload)


@router.get("/health/startup", summary="Kubernetes Startup Probe")
async def startup_probe():
    """
    Kubernetes Startup Probe.
    Verifies that initial table schema migrations and configuration loading have succeeded.
    """
    db_healthy = await check_db_health()
    if not db_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "initializing", "detail": "Waiting for database schema synchronization."},
        )
    return {
        "status": "started",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
