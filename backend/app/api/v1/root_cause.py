"""
INCIDENTX AI - Root Cause Intelligence REST API (Phase 11 Module 11.9)
Exposes endpoints for:
- Competing Hypothesis Generation & Ranking
- Active Counter-Evidence Disproof Reports
- Interactive Causal Graphs
- Historical Incident Matching & Recurrence Detection
- Comprehensive Root Cause Reports
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.exceptions import EntityNotFoundException
from backend.app.repositories.incident import IncidentRepository
from backend.app.services.root_cause.root_cause_service import root_cause_service
from backend.app.services.root_cause.schemas import (
    CausalGraph,
    CompetingHypothesisAnalysis,
    CounterEvidenceReport,
    HypothesisItem,
    RootCauseReport,
    SimilarIncidentMatch,
)

router = APIRouter(prefix="/incidents/{incident_id}/root-cause", tags=["Root Cause Intelligence"])


@router.post("/evaluate", response_model=RootCauseReport)
async def evaluate_root_cause(
    incident_id: str,
    affected_service: Optional[str] = Query(None, description="Override affected service target"),
    db: AsyncSession = Depends(get_db),
) -> RootCauseReport:
    """
    Executes the autonomous Phase 11 Root Cause Intelligence evaluation:
    Multi-domain correlation, competing hypothesis generation, active counter-evidence
    disproof, explainable confidence scoring, causal graph synthesis, and historical matching.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
        affected_service=affected_service,
    )
    return report


@router.get("/report", response_model=RootCauseReport)
async def get_root_cause_report(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> RootCauseReport:
    """
    Retrieves the full Phase 11 Root Cause Intelligence report for an incident.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
    )
    return report


@router.get("/hypotheses", response_model=CompetingHypothesisAnalysis)
async def get_competing_hypotheses(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> CompetingHypothesisAnalysis:
    """
    Retrieves competing hypotheses evaluated simultaneously with shared vs.
    discriminating evidence and comparative ranking explanations.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
    )
    return report.competing_analysis


@router.get("/counter-evidence", response_model=List[CounterEvidenceReport])
async def get_counter_evidence(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[CounterEvidenceReport]:
    """
    Retrieves the active counter-evidence disproof analysis and contradiction penalties.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
    )
    return report.counter_evidence_reports


@router.get("/causal-graph", response_model=CausalGraph)
async def get_causal_graph(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> CausalGraph:
    """
    Retrieves the directed Causal Graph distinguishing verified causal relationships
    from inferred correlations and assumptions.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
    )
    return report.causal_graph


@router.get("/similar-incidents", response_model=List[SimilarIncidentMatch])
async def get_similar_incidents(
    incident_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> List[SimilarIncidentMatch]:
    """
    Retrieves historically similar incidents from real database records to detect
    recurring operational failures.
    """
    inc_repo = IncidentRepository(db)
    incident = await inc_repo.get_by_id(incident_id)
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident_id,
        session=db,
    )
    return report.similar_incidents[:limit]
