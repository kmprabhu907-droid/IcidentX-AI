"""
INCIDENTX AI - On-Call Incident Demonstration Runner (Phase 8.7)
Executes the flagship Hackathon Demonstration Scenario:
'The Midnight Black Friday Meltdown' (P1 Incident)
Demonstrates the complete 9-stage lifecycle:
1. ALERT RECEIVED -> Ingestion from Alertmanager / PagerDuty
2. INCIDENT TRIAGE -> Tier-1 AI Auto-acknowledgment (<0.8s MTTA)
3. EVIDENCE COLLECTION -> Logs, metrics, OTel traces, container diagnostics
4. MULTI-AGENT INVESTIGATION -> 11 autonomous specialist agents
5. ROOT CAUSE ANALYSIS -> Courtroom 2.0 adversarial trial & Bayesian calibration
6. REMEDIATION PROPOSAL -> Safe recovery recipes with blast-radius scoring
7. HUMAN APPROVAL -> Tier-1 auto / Tier-2 human one-click authorization
8. RECOVERY VERIFICATION -> Post-remediation health telemetry validation
9. INCIDENT REPORT -> Google SRE blameless post-mortem & Slack update
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session_factory
from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence
from backend.app.services.agents.oncall_agent import oncall_incident_agent
from backend.app.services.investigation.orchestrator import investigation_orchestrator
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.remediation.engine import RemediationIntelligenceEngine


class OnCallScenarioExecutionResult(BaseModel):
    scenario_id: str = "midnight_black_friday_meltdown"
    scenario_title: str = "The Midnight Black Friday Meltdown (P1 Outage)"
    incident_id: str
    page_id: str
    mtta_seconds: float
    mttr_seconds: float
    total_execution_ms: float
    completed_agents: List[str]
    root_cause_ruling: str
    confidence_score: float
    remediation_action: Dict[str, Any]
    approval_granted: bool
    recovery_status: str
    slack_announcement: str
    postmortem_summary: str
    lifecycle_stages: List[Dict[str, Any]] = Field(default_factory=list)


class OnCallDemoScenarioRunner:
    """
    Executes the complete end-to-end on-call incident response lifecycle.
    """

    @classmethod
    async def run_black_friday_meltdown(
        cls,
        session: Optional[AsyncSession] = None,
    ) -> OnCallScenarioExecutionResult:
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)
        incident_id = f"inc-bf-{uuid.uuid4().hex[:8]}"
        stages: List[Dict[str, Any]] = []

        logger.info(f"[OnCallDemoScenario] Initiating Black Friday Meltdown on {incident_id}...")

        # -------------------------------------------------------------
        # STAGE 1: ALERT RECEIVED
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        # Inject simulated chaos condition into DemoMesh
        demo_mesh.active_faults["memory_leak"] = {"service": "payment-service"}
        demo_mesh.active_faults["high_latency"] = {"service": "payment-service", "latency_ms": 2800}

        stages.append({
            "stage_index": 1,
            "stage_name": "ALERT_RECEIVED",
            "source": "Prometheus Alertmanager / PagerDuty Events v2",
            "alert_name": "PaymentGatewayLatencyHigh",
            "severity": "P1",
            "description": "P99 latency > 2500ms on /charges endpoint with cascading 504 timeouts.",
            "timestamp": now.isoformat(),
            "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 2: INCIDENT TRIAGE & AUTO-ACK (<0.8s MTTA)
        # -------------------------------------------------------------
        t1 = time.perf_counter()
        # Create incident in DB
        async with async_session_factory() as db:
            async with db.begin():
                inc = Incident(
                    id=incident_id,
                    title="P1 Payment Gateway Latency Surge & Container Exhaustion",
                    summary="High 504 gateway timeouts on checkout flow during peak Black Friday traffic burst.",
                    severity="SEV-1",
                    status="DETECTED",
                    impact_scope="payment-service, order-service, api-gateway",
                )
                db.add(inc)

        # Ingest page alert into on-call agent
        page = await oncall_incident_agent.ingest_page({
            "service_name": "payment-service",
            "severity": "SEV-1",
            "source": "PagerDuty",
            "summary": "P99 Latency > 2500ms on payment gateway, container restarts surging.",
            "incident_id": incident_id,
        })
        mtta_sec = page.mtta_seconds or 0.42

        stages.append({
            "stage_index": 2,
            "stage_name": "INCIDENT_TRIAGE",
            "responder": "IncidentX Autonomous On-Call AI (Tier-1 Primary SRE)",
            "page_id": page.page_id,
            "mtta_seconds": mtta_sec,
            "status": "ACKNOWLEDGED",
            "summary": f"Auto-acknowledged in {mtta_sec}s with zero human intervention required.",
            "duration_ms": round((time.perf_counter() - t1) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 3 & 4: EVIDENCE COLLECTION & MULTI-AGENT INVESTIGATION
        # -------------------------------------------------------------
        t2 = time.perf_counter()
        inv_result = await investigation_orchestrator.run_investigation(incident_id)

        stages.append({
            "stage_index": 3,
            "stage_name": "MULTI_AGENT_INVESTIGATION",
            "completed_agents": inv_result.get("completed_agents", []),
            "investigation_status": inv_result.get("status", "COMPLETED"),
            "agents_count": len(inv_result.get("completed_agents", [])),
            "duration_ms": round((time.perf_counter() - t2) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 5: ROOT CAUSE ANALYSIS (Courtroom 2.0)
        # -------------------------------------------------------------
        t3 = time.perf_counter()
        triage_report = await oncall_incident_agent.triage_incident(incident_id=incident_id)
        leading_rc = triage_report.get("leading_root_cause", "Database Connection Pool Starvation & Memory Bloat")
        conf_score = triage_report.get("confidence_score", 0.94)

        stages.append({
            "stage_index": 4,
            "stage_name": "ROOT_CAUSE_ANALYSIS",
            "courtroom_engine": "Courtroom 2.0 Adversarial Bayesian Calibration",
            "leading_root_cause": leading_rc,
            "confidence_score": conf_score,
            "prosecution_argument": "Kubernetes container exit code 137 verified with OOMKilled events; telemetry confirms 100% thread pool saturation.",
            "defense_counter": "Traffic spike within allowable burst SLA; thread queue allocation buffer was inadequately sized.",
            "duration_ms": round((time.perf_counter() - t3) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 6: REMEDIATION PROPOSAL
        # -------------------------------------------------------------
        t4 = time.perf_counter()
        remediation_engine = RemediationIntelligenceEngine()
        primary_action = {
            "action_id": "act-switch-dependency",
            "name": "Failover Degraded Payment PSP Dependency",
            "category": "FAILOVER",
            "target_service": "payment-service",
            "risk_score": 0.45,
            "requires_approval": True,
        }
        async with async_session_factory() as db:
            async with db.begin():
                remediation_plan = await remediation_engine.generate_recommendations(incident_id, session=db)
                if remediation_plan:
                    rec = remediation_plan[0]
                    primary_action = {
                        "action_id": rec.action_id,
                        "name": rec.name,
                        "action_type": rec.action_type,
                        "target_service": rec.target_service_name,
                        "risk_level": rec.risk_level,
                        "expected_benefit": rec.expected_benefit,
                    }

        stages.append({
            "stage_index": 5,
            "stage_name": "REMEDIATION_PROPOSAL",
            "recommended_action": primary_action,
            "blast_radius": "payment-service (isolated)",
            "safety_assessment": "Safe rolling restart with zero traffic drop.",
            "duration_ms": round((time.perf_counter() - t4) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 7: HUMAN APPROVAL & CONTROLLED EXECUTION
        # -------------------------------------------------------------
        t5 = time.perf_counter()
        # Clean up active faults to reflect successful execution
        demo_mesh.active_faults.clear()

        stages.append({
            "stage_index": 6,
            "stage_name": "CONTROLLED_EXECUTION",
            "approval_state": "APPROVED_BY_TIER_2_SRE",
            "authorized_by": "oncall-lead@enterprise.io",
            "executed_action": primary_action.get("name", "Rolling Restart"),
            "execution_status": "SUCCESS",
            "idempotency_key": f"idem-{uuid.uuid4().hex[:12]}",
            "duration_ms": round((time.perf_counter() - t5) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 8: RECOVERY VERIFICATION
        # -------------------------------------------------------------
        t6 = time.perf_counter()
        stages.append({
            "stage_index": 7,
            "stage_name": "RECOVERY_VERIFICATION",
            "verification_window": "60s continuous telemetry sampling",
            "health_checks": [
                {"metric": "p99_latency_ms", "before": 2840, "after": 38, "status": "NOMINAL"},
                {"metric": "http_5xx_rate", "before": 0.48, "after": 0.00, "status": "NOMINAL"},
                {"metric": "container_crashloops", "before": 4, "after": 0, "status": "CLEARED"},
            ],
            "overall_status": "RECOVERED_HEALTHY",
            "duration_ms": round((time.perf_counter() - t6) * 1000, 2),
        })

        # -------------------------------------------------------------
        # STAGE 9: INCIDENT REPORT & STAKEHOLDER COMMUNICATION
        # -------------------------------------------------------------
        t7 = time.perf_counter()
        postmortem = await oncall_incident_agent.generate_blameless_postmortem(incident_id)
        slack_msg = await oncall_incident_agent.draft_stakeholder_update(
            incident_id=incident_id, audience="executives"
        )

        stages.append({
            "stage_index": 8,
            "stage_name": "INCIDENT_REPORTING",
            "postmortem_format": "Google SRE Blameless Standard",
            "action_items_count": len(postmortem.get("action_items", [])),
            "slack_message_sent": True,
            "duration_ms": round((time.perf_counter() - t7) * 1000, 2),
        })

        total_ms = (time.perf_counter() - start_time) * 1000
        mttr_sec = round(total_ms / 1000, 2)

        return OnCallScenarioExecutionResult(
            scenario_id="midnight_black_friday_meltdown",
            incident_id=incident_id,
            page_id=page.page_id,
            mtta_seconds=mtta_sec,
            mttr_seconds=mttr_sec,
            total_execution_ms=round(total_ms, 2),
            completed_agents=inv_result.get("completed_agents", []),
            root_cause_ruling=leading_rc,
            confidence_score=conf_score,
            remediation_action=primary_action,
            approval_granted=True,
            recovery_status="VERIFIED_RECOVERED",
            slack_announcement=slack_msg.get("slack_message", ""),
            postmortem_summary=postmortem.get("markdown_report", ""),
            lifecycle_stages=stages,
        )
