"""
INCIDENTX AI - Incidents API Router (Phase 9)
Endpoints for creating, listing, inspecting, transitioning, assigning, and streaming production incidents.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException, IncidentXException
from backend.app.models.incident import Incident
from backend.app.models.audit import AuditLog
from backend.app.repositories.incident import IncidentRepository
from backend.app.repositories.audit import AuditLogRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.incident import (
    IncidentAcknowledgeRequest,
    IncidentAssignRequest,
    IncidentCreate,
    IncidentEscalateRequest,
    IncidentOwnershipSummaryResponse,
    IncidentReassignRequest,
    IncidentResponse,
    IncidentStatisticsResponse,
    IncidentTransitionRequest,
    IncidentUpdate,
    TimelineEventResponse,
)
from backend.app.services.incident.lifecycle_engine import (
    IncidentLifecycleEngine,
    incident_lifecycle_engine,
)
from backend.app.services.incident.ownership_engine import incident_ownership_engine
from backend.app.services.incident.timeline_engine import incident_timeline_engine

router = APIRouter(prefix="/incidents", tags=["Incidents & Command Center"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = IncidentRepository(db)
    audit_repo = AuditLogRepository(db)

    norm_sev = IncidentLifecycleEngine.normalize_severity(payload.severity)

    incident = Incident(
        title=payload.title,
        summary=payload.summary,
        severity=payload.severity,
        status=payload.status or "DETECTED",
        priority=payload.priority or "HIGH",
        environment=payload.environment or "DEMOMESH",
        source=payload.source or "MANUAL",
        impact_scope=payload.impact_scope,
        owner_id=payload.owner_id,
        owner_name=payload.owner_name,
        assigned_team=payload.assigned_team or "Platform SRE",
        oncall_responder=payload.oncall_responder or "IncidentX AI (Tier-1)",
    )
    created = await repo.create(incident)

    # Initial timeline event
    await incident_timeline_engine.record_event(
        incident_id=created.id,
        event_type="DETECTION",
        service_name=created.impact_scope or "cluster",
        title=f"Incident Declared: {created.title}",
        description=f"Incident opened with severity {norm_sev} and status {created.status}. Environment: {created.environment}.",
        severity=norm_sev,
        actor=payload.owner_name or "IncidentX AI",
        actor_type="AI_AGENT" if not payload.owner_name else "HUMAN",
        data_source=created.environment or "DEMOMESH",
        session=db,
    )

    # Log audit event
    await audit_repo.create(
        AuditLog(
            incident_id=created.id,
            actor_type="USER",
            actor_id="api_client",
            action="INCIDENT_CREATED",
            resource_type="Incident",
            resource_id=created.id,
            details=f"Created incident: {created.title} ({norm_sev})",
        )
    )

    return created


@router.get("", response_model=PaginatedResponse[IncidentResponse])
async def list_incidents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    environment: Optional[str] = Query(default=None, description="Filter by environment"),
    owner_id: Optional[str] = Query(default=None, description="Filter by owner ID"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    search: Optional[str] = Query(default=None, description="Search by title, summary or affected service"),
    db: AsyncSession = Depends(get_db)
):
    repo = IncidentRepository(db)
    items, total = await repo.list_incidents(
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        environment=environment,
        owner_id=owner_id,
        priority=priority,
        search=search,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/statistics/summary", response_model=IncidentStatisticsResponse)
async def get_incident_statistics(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated incident lifecycle, severity, MTTA, MTTR, and environment statistics.
    """
    stmt = select(Incident)
    res = await db.execute(stmt)
    all_incidents = list(res.scalars().all())

    active_incidents = [
        i for i in all_incidents if i.status not in ("RESOLVED", "CLOSED", "CANCELLED")
    ]

    p1 = sum(
        1 for i in active_incidents if IncidentLifecycleEngine.normalize_severity(i.severity) == "P1"
    )
    p2 = sum(
        1 for i in active_incidents if IncidentLifecycleEngine.normalize_severity(i.severity) == "P2"
    )
    p3 = sum(
        1 for i in active_incidents if IncidentLifecycleEngine.normalize_severity(i.severity) == "P3"
    )
    p4 = sum(
        1 for i in active_incidents if IncidentLifecycleEngine.normalize_severity(i.severity) == "P4"
    )
    investigating = sum(1 for i in active_incidents if i.status == "INVESTIGATING")
    unassigned = sum(
        1 for i in active_incidents if not i.owner_id or i.owner_name in (None, "Unassigned", "")
    )
    resolved_count = sum(1 for i in all_incidents if i.status in ("RESOLVED", "CLOSED"))

    # MTTA calculation (time to acknowledge)
    ack_deltas: List[float] = []
    for i in all_incidents:
        if i.acknowledged_at and i.detected_at:
            ack = (
                i.acknowledged_at.replace(tzinfo=timezone.utc)
                if i.acknowledged_at.tzinfo is None
                else i.acknowledged_at
            )
            det = (
                i.detected_at.replace(tzinfo=timezone.utc)
                if i.detected_at.tzinfo is None
                else i.detected_at
            )
            delta = (ack - det).total_seconds()
            if delta >= 0:
                ack_deltas.append(delta)
    mean_mtta = sum(ack_deltas) / len(ack_deltas) if ack_deltas else 0.0

    # MTTR calculation (time to resolve)
    resolve_deltas: List[float] = []
    for i in all_incidents:
        if i.mttr_seconds is not None and i.mttr_seconds >= 0:
            resolve_deltas.append(i.mttr_seconds)
        elif i.resolved_at and i.detected_at:
            res = (
                i.resolved_at.replace(tzinfo=timezone.utc)
                if i.resolved_at.tzinfo is None
                else i.resolved_at
            )
            det = (
                i.detected_at.replace(tzinfo=timezone.utc)
                if i.detected_at.tzinfo is None
                else i.detected_at
            )
            delta = (res - det).total_seconds()
            if delta >= 0:
                resolve_deltas.append(delta)
    mean_mttr = sum(resolve_deltas) / len(resolve_deltas) if resolve_deltas else 0.0

    # Environment breakdown
    env_counts: Dict[str, int] = {}
    for i in all_incidents:
        env_name = i.environment or "DEMOMESH"
        env_counts[env_name] = env_counts.get(env_name, 0) + 1

    return IncidentStatisticsResponse(
        total_active=len(active_incidents),
        p1_critical=p1,
        p2_high=p2,
        p3_medium=p3,
        p4_low=p4,
        investigating=investigating,
        unassigned=unassigned,
        resolved_count=resolved_count,
        mean_time_to_acknowledge_seconds=round(mean_mtta, 2),
        mean_time_to_resolve_seconds=round(mean_mttr, 2),
        environment_counts=env_counts,
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


@router.post("/{incident_id}/transition", response_model=IncidentResponse)
async def transition_incident(
    incident_id: str,
    payload: IncidentTransitionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes a validated lifecycle transition (Module 9.1).
    Validates state matrix, stamps timestamps, and records immutable audit/timeline entries.
    """
    updated = await incident_lifecycle_engine.transition(
        incident_id=incident_id,
        target_state=payload.target_state,
        actor=payload.actor,
        actor_type=payload.actor_type,
        reason=payload.reason,
        session=db,
    )
    return updated


@router.get("/{incident_id}/timeline", response_model=List[TimelineEventResponse])
async def get_incident_timeline(
    incident_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    event_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns ordered chronological timeline events for the incident (Module 9.2).
    """
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    events = await incident_timeline_engine.list_events(
        incident_id=incident_id,
        session=db,
        limit=limit,
        offset=offset,
        event_type=event_type,
    )
    return events


@router.get("/{incident_id}/timeline/stream")
async def stream_incident_timeline(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) live stream of incident events and heartbeats (Module 9.2).
    """
    repo = IncidentRepository(db)
    incident = await repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    return StreamingResponse(
        incident_timeline_engine.event_generator(incident_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident_owner(
    incident_id: str,
    payload: IncidentAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Assigns an owner/responder and team to an incident (Module 9.4).
    """
    updated = await incident_ownership_engine.assign_owner(
        incident_id=incident_id,
        assigned_to_id=payload.assigned_to_id,
        assigned_to_name=payload.assigned_to_name,
        team_name=payload.team_name,
        assigned_by=payload.assigned_by,
        role=payload.role,
        reason=payload.reason,
        session=db,
    )
    return updated


@router.post("/{incident_id}/reassign", response_model=IncidentResponse)
async def reassign_incident_owner(
    incident_id: str,
    payload: IncidentReassignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reassigns an incident to a new responder with required justification (Module 9.4).
    """
    updated = await incident_ownership_engine.reassign_owner(
        incident_id=incident_id,
        new_owner_id=payload.new_owner_id,
        new_owner_name=payload.new_owner_name,
        new_team_name=payload.new_team_name,
        assigned_by=payload.assigned_by,
        reason=payload.reason,
        session=db,
    )
    return updated


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: str,
    payload: IncidentAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledges an incident and records responder acknowledgment timestamp (Module 9.4).
    """
    updated = await incident_ownership_engine.acknowledge_incident(
        incident_id=incident_id,
        responder_id=payload.responder_id,
        responder_name=payload.responder_name,
        session=db,
    )
    return updated


@router.post("/{incident_id}/escalate", response_model=IncidentResponse)
async def escalate_incident(
    incident_id: str,
    payload: IncidentEscalateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Escalates an incident to higher responder tier with paging reason (Module 9.4).
    """
    updated = await incident_ownership_engine.escalate_incident(
        incident_id=incident_id,
        reason=payload.reason,
        target_tier=payload.target_tier,
        escalated_by=payload.escalated_by,
        session=db,
    )
    return updated


@router.get("/{incident_id}/ownership", response_model=IncidentOwnershipSummaryResponse)
async def get_incident_ownership(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns incident ownership metadata, escalation status, and assignment history (Module 9.4).
    """
    summary = await incident_ownership_engine.get_ownership_summary(
        incident_id=incident_id,
        session=db,
    )
    return summary
