"""
INCIDENTX AI - Investigation API Router
Returns genuine stored evidence, hypotheses, and agent executions for an incident.
Never fabricates mock data; returns true stored records or an empty collection.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException
from backend.app.repositories.incident import IncidentRepository
from backend.app.repositories.investigation import (
    AgentExecutionRepository,
    EvidenceRepository,
    HypothesisRepository,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.investigation import (
    AgentExecutionResponse,
    EvidenceResponse,
    HypothesisResponse,
)

router = APIRouter(prefix="/incidents/{incident_id}", tags=["Investigation & Courtroom"])


@router.get("/evidence", response_model=PaginatedResponse[EvidenceResponse])
async def get_incident_evidence(
    incident_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    repo = EvidenceRepository(db)
    items, total = await repo.list_by_incident(incident_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/hypotheses", response_model=PaginatedResponse[HypothesisResponse])
async def get_incident_hypotheses(
    incident_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    repo = HypothesisRepository(db)
    items, total = await repo.list_by_incident(incident_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/agent-executions", response_model=PaginatedResponse[AgentExecutionResponse])
async def get_incident_agent_executions(
    incident_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    repo = AgentExecutionRepository(db)
    items, total = await repo.list_by_incident(incident_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )
