"""
INCIDENTX AI - Alerts API Router (Phase 9 Module 9.3)
Exposes unified ingestion endpoints for Prometheus Alertmanager, Grafana Alerting,
Kubernetes Warning Events, OpenTelemetry signals, and custom webhooks.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.alert import Alert
from backend.app.schemas.alert import AlertIngestRequest, AlertIngestResponse, AlertResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.services.incident.alert_ingestion_engine import alert_ingestion_engine

router = APIRouter(prefix="/alerts", tags=["Intelligent Alert Ingestion Engine"])


@router.post(
    "/ingest",
    response_model=AlertIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Unified Alert Ingestion Webhook",
    description="Accepts inbound alerts from Prometheus Alertmanager, Grafana, Kubernetes events, and custom webhooks. Enforces deduplication and creates or correlates with active incidents.",
)
async def ingest_alert(
    request: Request,
    payload: Optional[Dict[str, Any]] = Body(None),
    source: Optional[str] = Query(None, description="Explicit source identifier override"),
    db: AsyncSession = Depends(get_db),
):
    try:
        body = payload or await request.json()
    except Exception:
        body = {}

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be a valid JSON body.",
        )

    result = await alert_ingestion_engine.ingest_alert(
        payload_data=body,
        session=db,
        source_override=source,
    )
    return result


@router.get(
    "",
    response_model=PaginatedResponse[AlertResponse],
    summary="List Ingested Alerts",
)
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service_name: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    incident_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert)
    if service_name:
        query = query.where(Alert.service_name == service_name)
    if severity:
        query = query.where(Alert.severity == severity)
    if source:
        query = query.where(Alert.source == source)
    if status:
        query = query.where(Alert.status == status)
    if incident_id:
        query = query.where(Alert.incident_id == incident_id)

    # Count
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Paginate
    query = query.order_by(desc(Alert.last_seen_at)).limit(page_size).offset((page - 1) * page_size)
    res = await db.execute(query)
    items = list(res.scalars().all())

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get Alert Details",
)
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Alert).where(Alert.id == alert_id)
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return alert
