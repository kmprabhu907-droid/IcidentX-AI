"""
INCIDENTX AI - Reliability API Endpoints (Phase 5)
Provides API access to:
  - Stage 5.4: Reliability Memory Engine (historical incidents, multi-feature search,
    fingerprint similarity ranking with 6 explainable answers, remediation learning)
  - Stage 5.5: Predictive Reliability Intelligence
  - Stage 5.6: SLO & Error Budget Intelligence
  - Stage 5.7: Incident Time Machine & Chronological Replay
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.incident import Incident
from backend.app.models.remediation import RemediationAction
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.regression.fingerprint import FingerprintBuilder
from backend.app.services.reliability_memory.engine import ReliabilityMemoryEngine
from backend.app.services.reliability_memory.remediation_learner import (
    RemediationLearner,
    SIDE_EFFECT_REGISTRY,
)
from backend.app.services.predictive import PredictiveReliabilityEngine
from backend.app.services.slo import SLOIntelligenceEngine
from backend.app.services.time_machine import IncidentTimeMachineEngine

router = APIRouter(prefix="/reliability", tags=["Reliability Intelligence"])


class MemorySearchRequest(BaseModel):
    query_text: Optional[str] = Field(None, description="Keyword text search across titles, summaries, error logs")
    service_name: Optional[str] = Field(None, description="Filter by primary or affected service")
    severity: Optional[str] = Field(None, description="Filter by severity level (SEV-1, SEV-2, SEV-3, SEV-4)")
    root_cause_category: Optional[str] = Field(None, description="Filter by root cause category")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of historical records to return")


# ============================================================================
# STAGE 5.4: RELIABILITY MEMORY ENDPOINTS
# ============================================================================

@router.get("/memory/incidents")
async def list_historical_incidents(
    service_name: Optional[str] = Query(None, description="Filter by affected service"),
    severity: Optional[str] = Query(None, description="Filter by severity (SEV-1, SEV-2, etc.)"),
    category: Optional[str] = Query(None, description="Filter by root cause category"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List historical incident memory entries with multi-attribute filtering and pagination.
    """
    entries = await ReliabilityMemoryEngine.search_memory(
        db=db,
        service_name=service_name,
        severity=severity,
        root_cause_category=category,
        limit=limit + offset,
    )
    paged = entries[offset : offset + limit]
    return {
        "total": len(entries),
        "limit": limit,
        "offset": offset,
        "items": [e.to_dict() for e in paged],
    }


@router.get("/memory/incidents/{incident_id}")
async def get_incident_memory(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve the full 20-dimension historical memory record for a specific incident.
    """
    entry = await ReliabilityMemoryEngine.build_memory_entry(incident_id, db)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Historical memory entry for incident '{incident_id}' not found.",
        )
    return entry.to_dict()


@router.post("/memory/search")
async def search_incident_memory(
    request: MemorySearchRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Perform multi-criteria keyword and structured metadata search across indexed incident memories.
    """
    results = await ReliabilityMemoryEngine.search_memory(
        db=db,
        query_text=request.query_text,
        service_name=request.service_name,
        severity=request.severity,
        root_cause_category=request.root_cause_category,
        limit=request.limit,
    )
    return {
        "query": request.model_dump(),
        "count": len(results),
        "matches": [r.to_dict() for r in results],
    }


@router.get("/memory/remediation-history")
async def get_remediation_history(
    action_id: Optional[str] = Query(None, description="Specific action ID (e.g. act-clear-cache)"),
    target_service: Optional[str] = Query(None, description="Filter by service name"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Synthesize empirical remediation learning, success rates, side effects, and reusable advice.
    """
    if action_id:
        summary = await RemediationLearner.get_action_learning(
            action_id=action_id,
            db=db,
            target_service=target_service,
        )
        return {"action_learning": summary.to_dict()}

    # Gather learning across all registered and known actions
    distinct_q = select(RemediationAction.action_id).distinct()
    res = await db.execute(distinct_q)
    known_actions = set(res.scalars().all())
    known_actions.update(SIDE_EFFECT_REGISTRY.keys())

    summaries = []
    for act_id in sorted(known_actions):
        s = await RemediationLearner.get_action_learning(
            action_id=act_id,
            db=db,
            target_service=target_service,
        )
        summaries.append(s.to_dict())

    return {
        "target_service": target_service or "all",
        "total_action_types": len(summaries),
        "actions": summaries,
    }


@router.get("/memory/similar-incidents")
async def find_similar_incidents(
    incident_id: Optional[str] = Query(None, description="Target incident ID to match against"),
    service_name: Optional[str] = Query(None, description="Target service name if no incident ID provided"),
    min_similarity: float = Query(0.25, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0 - 1.0)"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of similar incidents to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve historical incidents ranked by multi-dimensional fingerprint similarity,
    complete with the 6 standard memory explanation answers.
    """
    target_fp = None

    if incident_id:
        target_entry = await ReliabilityMemoryEngine.build_memory_entry(incident_id, db)
        if not target_entry:
            raise HTTPException(
                status_code=404,
                detail=f"Target incident '{incident_id}' not found for similarity comparison.",
            )
        target_fp = FingerprintBuilder.build(
            incident_id=target_entry.incident_id,
            primary_service=target_entry.primary_service,
            affected_services=target_entry.affected_services,
            telemetry_anomalies=target_entry.telemetry_patterns,
            error_logs=target_entry.error_signatures,
            hypotheses=[target_entry.summary] + [h["hypothesis_text"] for h in target_entry.hypotheses],
            severity=target_entry.severity,
        )
    elif service_name:
        # Build synthetic fingerprint from current service metrics
        latest = demo_mesh.get_latest_metrics().get(service_name, {})
        anomalies: Dict[str, float] = {}
        if latest.get("error_rate", 0) > 0.05:
            anomalies["error_rate"] = float(latest["error_rate"]) * 100.0
        if latest.get("cpu_utilization", 0) > 80.0:
            anomalies["cpu_utilization"] = float(latest["cpu_utilization"])
        if latest.get("db_pool_utilization", 0) > 80.0:
            anomalies["db_pool_utilization"] = float(latest["db_pool_utilization"])

        target_fp = FingerprintBuilder.build(
            incident_id=f"live-eval-{service_name}",
            primary_service=service_name,
            affected_services=[service_name],
            telemetry_anomalies=anomalies,
            error_logs=[],
            hypotheses=[f"Live degradation observed on {service_name}"],
            severity="SEV-2",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'incident_id' or 'service_name' must be provided.",
        )

    matches = await ReliabilityMemoryEngine.find_similar_incidents(
        target_fingerprint=target_fp,
        db=db,
        min_similarity=min_similarity,
        limit=limit,
    )

    return {
        "target": {
            "incident_id": target_fp.incident_id,
            "primary_service": target_fp.primary_service,
            "affected_services": list(target_fp.affected_services),
            "root_cause_categories": list(target_fp.root_cause_categories),
        },
        "match_count": len(matches),
        "min_similarity": min_similarity,
        "similar_incidents": matches,
    }


# ============================================================================
# STAGE 5.5: PREDICTIVE RELIABILITY ENDPOINTS
# ============================================================================

@router.get("/predictions")
async def get_active_predictions(
    service_name: Optional[str] = Query(None, description="Optional service name filter"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve streaming resource trend models, growth rates, and Time-to-Exhaustion (TTE) projections.
    """
    preds = await PredictiveReliabilityEngine.get_active_predictions(
        service_name=service_name,
        db=db,
    )
    return {
        "service_name": service_name or "all",
        "count": len(preds),
        "predictions": preds,
    }


@router.get("/forecast/{service_id}")
async def get_service_forecast(
    service_id: str,
    metric_name: Optional[str] = Query(None, description="Specific metric to forecast"),
    horizon_seconds: int = Query(1800, ge=60, le=7200, description="Forward projection horizon in seconds"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate forward forecast data points with 95% confidence intervals and exhaustion alerts.
    """
    # Map service_id to name if UUID provided
    uuid_to_name = {v: k for k, v in demo_mesh.SERVICE_ID_MAP.items()}
    target_name = uuid_to_name.get(service_id, service_id)

    forecast = await PredictiveReliabilityEngine.get_service_forecast(
        service_name=target_name,
        metric_name=metric_name,
        horizon_seconds=horizon_seconds,
        db=db,
    )
    return forecast


@router.get("/capacity-risk")
async def get_capacity_risks(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Synthesize cluster-wide capacity risks, ranked by shortest TTE and exhaustion hazard,
    with prescriptive prevention recommendations.
    """
    risks = await PredictiveReliabilityEngine.get_capacity_risks(db=db)
    return {
        "count": len(risks),
        "risks": risks,
    }


# ============================================================================
# STAGE 5.6: SLO & ERROR BUDGET ENDPOINTS
# ============================================================================

@router.get("/slo")
async def list_slos(
    service_name: Optional[str] = Query(None, description="Optional service name filter"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List all active Service Level Objectives (SLOs) with current real-time SLI measurements
    and remaining error budget percentages.
    """
    slos = await SLOIntelligenceEngine.get_all_slos_status(
        service_name=service_name,
        db=db,
    )
    return {
        "service_name": service_name or "all",
        "count": len(slos),
        "slos": slos,
    }


@router.get("/error-budget")
async def get_error_budgets(
    service_name: Optional[str] = Query(None, description="Optional service name filter"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve comprehensive error budget status, total allowed budget, consumption rate,
    and operational exhaustion health tiers.
    """
    budgets = await SLOIntelligenceEngine.get_error_budgets(
        service_name=service_name,
        db=db,
    )
    return {
        "service_name": service_name or "all",
        "count": len(budgets),
        "error_budgets": budgets,
    }


@router.get("/burn-rate")
async def get_burn_rates(
    service_name: Optional[str] = Query(None, description="Optional service name filter"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Evaluate multi-window burn rate intelligence (1h, 6h, 24h, 3d, 14d, 30d) and trigger
    Google SRE fast-burn (>14.4x) and slow-burn (>1.0x) alerts.
    """
    burn_rates = await SLOIntelligenceEngine.get_burn_rates(
        service_name=service_name,
        db=db,
    )
    return {
        "service_name": service_name or "all",
        "count": len(burn_rates),
        "burn_rates": burn_rates,
    }


# ============================================================================
# STAGE 5.7: INCIDENT TIME MACHINE ENDPOINTS
# ============================================================================

@router.get("/time-machine/{incident_id}")
async def get_incident_time_machine(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Reconstruct the complete chronological lifecycle of an incident, correlating
    telemetry, anomalies, logs, traces, hypotheses, remediations, and causal graphs.
    """
    report = await IncidentTimeMachineEngine.build_incident_timeline(incident_id, db)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Incident '{incident_id}' not found for Time Machine reconstruction.",
        )
    return report.to_dict()


@router.get("/time-machine/{incident_id}/state-at/{timestamp}")
async def get_incident_state_at_timestamp(
    incident_id: str,
    timestamp: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Point-in-time infrastructure metrics and operational health reconstruction for historical replay.
    """
    snapshot = await IncidentTimeMachineEngine.get_state_at_timestamp(incident_id, timestamp, db)
    return snapshot.to_dict()


@router.get("/time-machine/{incident_id}/causal-graph")
async def get_incident_causal_graph(
    incident_id: str,
    phase: Optional[str] = Query(None, description="Optional lifecycle phase filter (e.g. DETECTION, MITIGATION)"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve topological NetworkX causal state, failure propagation paths, and blast radius scores.
    """
    causal_state = await IncidentTimeMachineEngine.get_causal_graph_state(incident_id, phase, db)
    return causal_state.to_dict()



