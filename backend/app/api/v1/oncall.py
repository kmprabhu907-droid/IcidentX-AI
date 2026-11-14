"""
INCIDENTX AI - On-Call Incident Agent API Router
Exposes endpoints for the 24/7 Autonomous On-Call Agent:
Shift status, pager ingestion, autonomous triage, interactive copilot chat,
Slack stakeholder communications, post-mortem generation, and human escalation.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.services.agents.oncall_agent import oncall_incident_agent

router = APIRouter(prefix="/oncall", tags=["Autonomous On-Call Incident Agent"])


class PageIngestRequest(BaseModel):
    service_name: str
    severity: str = "SEV-2"
    source: str = "PagerDuty"
    summary: str
    incident_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    incident_id: Optional[str] = None


class EscalateRequest(BaseModel):
    reason: str


@router.get("/status")
async def get_oncall_status() -> Dict[str, Any]:
    """
    Get the real-time status of the Autonomous On-Call Incident Agent,
    shift roster, active paging queue, and Mean Time to Acknowledge (MTTA) metrics.
    """
    return oncall_incident_agent.get_shift_status()


@router.post("/page")
async def ingest_pager_alert(
    payload: PageIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ingest a new incoming alert from PagerDuty, Opsgenie, Alertmanager, or Prometheus.
    Automatically acknowledges the alert within milliseconds to ensure sub-second MTTA.
    """
    page = await oncall_incident_agent.ingest_page(payload.model_dump(), db=db)
    return {
        "status": "ACKNOWLEDGED",
        "page": page.model_dump(),
        "message": f"Alert successfully ingested and auto-acknowledged in {page.mtta_seconds}s.",
    }


@router.post("/triage/{incident_id}")
async def triage_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger immediate autonomous on-call triage for an incident:
    evaluates telemetry evidence, formulates Courtroom 2.0 hypotheses, and recommends safe recovery actions.
    """
    try:
        triage_result = await oncall_incident_agent.triage_incident(incident_id=incident_id, db=db)
        return triage_result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"On-call triage failed: {str(e)}",
        )


@router.post("/chat")
async def chat_with_oncall_agent(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Converse directly with the Autonomous On-Call Incident Agent Copilot.
    Ask questions regarding active alerts, service blast radius, root causes, or mitigation plans.
    """
    reply = await oncall_incident_agent.chat(
        message=payload.message,
        incident_id=payload.incident_id,
        db=db,
    )
    return reply


@router.post("/update/{incident_id}/draft")
async def draft_stakeholder_update(
    incident_id: str,
    audience: str = Query("SLACK"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Draft an executive or engineering stakeholder incident communication formatted for Slack.
    """
    draft = await oncall_incident_agent.draft_stakeholder_update(
        incident_id=incident_id,
        audience=audience,
        db=db,
    )
    return draft


@router.post("/postmortem/{incident_id}")
async def generate_postmortem(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate a full blameless post-mortem report grounded in verified incident telemetry and Courtroom 2.0 findings.
    """
    report = await oncall_incident_agent.generate_blameless_postmortem(
        incident_id=incident_id,
        db=db,
    )
    return report


@router.post("/escalate/{page_id}")
async def escalate_page(
    page_id: str,
    payload: EscalateRequest,
) -> Dict[str, Any]:
    """
    Escalate an ongoing incident from Tier-1 Autonomous AI to Tier-2 Human SRE Team.
    """
    result = await oncall_incident_agent.escalate_to_human(
        page_id=page_id,
        reason=payload.reason,
    )
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    return result


@router.post("/scenarios/midnight-meltdown")
async def run_midnight_meltdown_demo(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Execute the flagship Black Friday Meltdown demonstration scenario across all 9 on-call lifecycle stages:
    Alert Ingestion -> MTTA Auto-Ack -> Multi-Agent Swarm -> Courtroom 2.0 -> Remediation -> Approval -> Recovery Verification -> Post-Mortem.
    """
    from backend.app.services.agents.oncall_demo_scenario import OnCallDemoScenarioRunner
    result = await OnCallDemoScenarioRunner.run_black_friday_meltdown(session=db)
    return result.model_dump()

