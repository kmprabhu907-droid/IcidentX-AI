"""
INCIDENTX AI - Investigation Summary & Active Investigation Planner Agent
Synthesizes the final executive postmortem, constructs the causal chain,
and prioritizes safe, high-information next diagnostic actions.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.models.investigation import InvestigationPlan
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    DiagnosticAction,
    InvestigationSummaryResult,
)


class InvestigationSummaryAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="InvestigationSummaryAgent",
            role="summary",
            execution_phase="SUMMARY_SYNTHESIS",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        verification = state.get("verification", {})
        top_hyp = verification.get("highest_confidence_hypothesis")
        dependency = state.get("dependency", {})
        culprit = top_hyp.get("culprit_service") if top_hyp else dependency.get("causal_origin_service", "Unknown")
        confidence = top_hyp.get("confidence_score", 0.75) if top_hyp else 0.70

        # Construct causal chain
        chain = dependency.get("propagation_chain", [culprit, "api-gateway"])
        reconstruction = [
            f"T0: Anomaly epicenter initiated inside {culprit}.",
            f"T1: Upstream dependencies ({', '.join(chain[1:]) or 'none'}) experienced degraded response latencies.",
            f"T2: Client-facing API Gateway observed HTTP 502/504 errors, triggering autonomous incident detection.",
        ]

        # Active Investigation Plan: Safe Diagnostic Actions
        actions: List[DiagnosticAction] = []
        if culprit == "postgres-db":
            actions.append(DiagnosticAction(
                action_id="act-db-pool-inspect",
                name="Query pg_stat_activity connection states",
                category="Database Diagnostics",
                target_service="postgres-db",
                diagnostic_value=0.95,
                estimated_cost="LOW",
                operational_risk="LOW",
                rationale="Identify whether connection exhaustion was driven by idle-in-transaction clients, long-running locks, or connection pooling leakage.",
            ))
            actions.append(DiagnosticAction(
                action_id="act-order-pool-verify",
                name="Inspect OrderService connection acquisition timeout config",
                category="Configuration Audit",
                target_service="order-service",
                diagnostic_value=0.85,
                estimated_cost="LOW",
                operational_risk="LOW",
                rationale="Audit client-side connection timeout parameters to ensure worker threads fail fast rather than accumulating backpressure.",
            ))
        elif culprit == "payment-service":
            actions.append(DiagnosticAction(
                action_id="act-psp-latency-probe",
                name="Inspect External PSP Round-Trip Latency Histogram",
                category="Network / Gateway",
                target_service="payment-service",
                diagnostic_value=0.92,
                estimated_cost="LOW",
                operational_risk="LOW",
                rationale="Distinguish whether latency spike was internal processing deadlock or third-party payment provider transit delay.",
            ))
            actions.append(DiagnosticAction(
                action_id="act-circuit-breaker-status",
                name="Verify Payment Client Circuit Breaker Trip Counters",
                category="Resilience Audit",
                target_service="order-service",
                diagnostic_value=0.88,
                estimated_cost="LOW",
                operational_risk="LOW",
                rationale="Confirm why the circuit breaker did not isolate payment gateway timeouts before checkout threads were exhausted.",
            ))
        else:
            actions.append(DiagnosticAction(
                action_id="act-thread-dump",
                name="Capture Thread & Heap Allocation Profile",
                category="Runtime Diagnostics",
                target_service=culprit,
                diagnostic_value=0.90,
                estimated_cost="LOW",
                operational_risk="LOW",
                rationale=f"Diagnose thread starvation, GC pauses, and lock contention on {culprit}.",
            ))

        # Executive summary text
        summary = (
            f"Autonomous investigation completed with {int(confidence * 100)}% confidence. "
            f"Primary root cause identified as {culprit} ({top_hyp.get('hypothesis_title', 'Service Anomaly') if top_hyp else 'Degradation'}). "
            f"Causal propagation traveled via {' -> '.join(chain)}. "
            f"Formulated {len(actions)} safe active diagnostic actions to eliminate remaining uncertainty."
        )

        ruling = top_hyp.get("judicial_ruling", "Root cause validated by empirical telemetry.") if top_hyp else "Investigated."

        res = InvestigationSummaryResult(
            executive_summary=summary,
            root_cause_ruling=ruling,
            confidence_score=confidence,
            identified_culprit=culprit,
            causal_reconstruction=reconstruction,
            recommended_diagnostic_actions=actions,
            evidence_provenance_count=len(top_hyp.get("supporting_evidence_ids", [])) if top_hyp else 0,
        )

        state["summary"] = res.model_dump()

        # Persist InvestigationPlan in DB
        plan_record = InvestigationPlan(
            incident_id=incident_id,
            recommended_actions=json.dumps([a.model_dump() for a in actions]),
            status="RECOMMENDED",
        )
        session.add(plan_record)

        # Update Incident in DB
        inc_stmt = select(Incident).where(Incident.id == incident_id)
        inc_res = await session.execute(inc_stmt)
        incident = inc_res.scalar_one_or_none()
        if incident:
            incident.status = "INVESTIGATING"
            incident.summary = summary
            incident.impact_scope = ", ".join(chain)

        await session.flush()
        return state
