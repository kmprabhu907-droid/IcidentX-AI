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
