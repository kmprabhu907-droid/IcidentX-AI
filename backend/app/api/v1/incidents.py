"""
INCIDENTX AI - Incidents API Router
Endpoints for creating, listing, and inspecting production incidents.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException
from backend.app.models.incident import Incident
from backend.app.models.audit import AuditLog
from backend.app.repositories.incident import IncidentRepository
from backend.app.repositories.audit import AuditLogRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.incident import IncidentCreate, IncidentResponse, IncidentUpdate

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = IncidentRepository(db)
    audit_repo = AuditLogRepository(db)

    incident = Incident(
        title=payload.title,
        summary=payload.summary,
        severity=payload.severity,
        status=payload.status,
        impact_scope=payload.impact_scope,
    )
    created = await repo.create(incident)

    # Log audit event
    await audit_repo.create(
        AuditLog(
            incident_id=created.id,
            actor_type="USER",
            actor_id="api_client",
            action="INCIDENT_CREATED",
            resource_type="Incident",
            resource_id=created.id,
            details=f"Created incident: {created.title} ({created.severity})",
        )
    )

    return created


@router.get("", response_model=PaginatedResponse[IncidentResponse])
async def list_incidents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    db: AsyncSession = Depends(get_db)
):
    repo = IncidentRepository(db)
    items, total = await repo.list_incidents(
        page=page, page_size=page_size, status=status, severity=severity
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)
    return incident
