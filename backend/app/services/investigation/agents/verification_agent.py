"""
INCIDENTX AI - Evidence Verification Agent
Evaluates competing hypotheses against collected evidence exhibits.
Calculates mathematical confidence scores, flags contradictions, and enforces
insufficient evidence rulings.
"""

from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.service import Service
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    VerificationResult,
    VerifiedHypothesisEvaluation,
)


class EvidenceVerificationAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="EvidenceVerificationAgent",
            role="verification",
            execution_phase="EVIDENCE_VERIFICATION",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        hypotheses_data = state.get("hypotheses", {}).get("competing_hypotheses", [])
        telemetry = state.get("telemetry", {})
        logs = state.get("logs", {})
        traces = state.get("traces", {})

        # 1. Fetch existing Evidence rows from DB
        ev_stmt = select(Evidence).where(Evidence.incident_id == incident_id)
        ev_res = await session.execute(ev_stmt)
        evidence_rows = list(ev_res.scalars().all())

        # If no DB evidence yet, generate verified exhibits from state
        if not evidence_rows:
            evidence_rows = await self._generate_evidence_exhibits(incident_id, state, session)

        evaluations: List[VerifiedHypothesisEvaluation] = []

        # 2. Evaluate each hypothesis
        for hyp_dict in hypotheses_data:
            culprit = hyp_dict.get("culprit_service", "")
            title = hyp_dict.get("title", "")

            supporting_ids: List[str] = []
            contradicting_ids: List[str] = []
            missing_evidence: List[str] = []

            w_support = 0.0
            w_contradict = 0.0

            for ev in evidence_rows:
                # Evidence matches culprit service
                if ev.affected_service_name == culprit or culprit in (ev.description or ""):
                    if ev.is_contradictory:
                        contradicting_ids.append(ev.id)
                        w_contradict += ev.confidence_score * 2.0  # Double penalty for contradictory evidence
                    else:
                        supporting_ids.append(ev.id)
                        w_support += ev.confidence_score
                else:
                    # Non-matching evidence could indicate alternative cause
                    if ev.confidence_score > 0.90 and "critical" in ev.description.lower():
                        contradicting_ids.append(ev.id)
                        w_contradict += 0.5

            # Identify missing evidence gaps
            if not any(ev.evidence_type == "trace_span" for ev in evidence_rows if ev.id in supporting_ids):
                missing_evidence.append(f"Direct distributed trace span verifying {culprit} failure")
            if not any(ev.evidence_type == "error_log" for ev in evidence_rows if ev.id in supporting_ids):
                missing_evidence.append(f"Explicit error log stack trace from {culprit}")

            # Confidence Formula:
            # Confidence = W_support / (W_support + W_contradict + (0.25 * MissingCount))
            missing_penalty = 0.25 * len(missing_evidence)
            denominator = w_support + w_contradict + missing_penalty
            if denominator > 0:
                raw_confidence = w_support / denominator
            else:
                raw_confidence = 0.20

            confidence = round(min(0.98, max(0.05, raw_confidence)), 2)

            # Judicial ruling & status assignment
            if len(supporting_ids) == 0 or confidence < 0.40:
                status = "INSUFFICIENT_EVIDENCE"
                ruling = f"Insufficient evidence to establish {culprit} as the root cause. Missing critical diagnostic proof."
            elif w_contradict > w_support:
                status = "DISPROVEN"
                ruling = f"Hypothesis refuted by contradictory evidence exhibits showing alternative failure propagation."
            elif confidence >= 0.75:
                status = "VALIDATED"
                ruling = f"Root cause verified with high confidence ({int(confidence * 100)}%). Supported by {len(supporting_ids)} empirical exhibits."
            else:
                status = "UNDER_CROSS_EXAMINATION"
                ruling = f"Plausible contributing factor ({int(confidence * 100)}% confidence). Further diagnostic verification required."

            evaluations.append(VerifiedHypothesisEvaluation(
                hypothesis_title=title,
                culprit_service=culprit,
                confidence_score=confidence,
                supporting_evidence_ids=supporting_ids,
                contradictory_evidence_ids=contradicting_ids,
                missing_evidence=missing_evidence,
                status=status,
                judicial_ruling=ruling,
            ))

            # Persist / Update RootCauseHypothesis in DB
            await self._persist_hypothesis(incident_id, hyp_dict, confidence, status, ruling, session)

        # Select highest confidence hypothesis
        evaluations.sort(key=lambda e: e.confidence_score, reverse=True)
        top = evaluations[0] if evaluations else None

        res = VerificationResult(
            evaluations=evaluations,
            highest_confidence_hypothesis=top,
            evidence_sufficiency_verdict="SUFFICIENT" if (top and top.confidence_score >= 0.70) else "INSUFFICIENT",
        )

        state["verification"] = res.model_dump()
        return state

    async def _generate_evidence_exhibits(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> List[Evidence]:
        """Generate structured Evidence records with full provenance."""
        exhibits: List[Evidence] = []
        telemetry = state.get("telemetry", {})
        logs = state.get("logs", {})
        traces = state.get("traces", {})

        # 1. Telemetry evidence
        for anom in telemetry.get("anomalous_metrics", []):
            ev = Evidence(
                incident_id=incident_id,
                evidence_type="metric_anomaly",
                source_system="prometheus",
                affected_service_name=anom.get("service_name"),
                raw_source_ref=f"metric:{anom.get('metric_name')}",
                description=anom.get("observation", ""),
                relevant_observation=f"Observed value {anom.get('current_value')} vs baseline {anom.get('baseline_value')}",
                confidence_score=0.92,
                is_contradictory=False,
                verification_status="VERIFIED",
            )
            session.add(ev)
            exhibits.append(ev)

        # 2. Log evidence
        for cluster in logs.get("exception_clusters", []):
            ev = Evidence(
                incident_id=incident_id,
                evidence_type="error_log",
                source_system="loki",
                affected_service_name=cluster.get("service_name"),
                raw_source_ref=f"log_cluster:{cluster.get('signature')}",
                description=cluster.get("sample_message", ""),
                relevant_observation=f"Exception cluster '{cluster.get('signature')}' occurred {cluster.get('count')} times",
                confidence_score=0.95,
                is_contradictory=False,
                verification_status="VERIFIED",
            )
            session.add(ev)
            exhibits.append(ev)

        # 3. Trace evidence
        for span in traces.get("slowest_spans", []):
            ev = Evidence(
                incident_id=incident_id,
                evidence_type="trace_span",
                source_system="opentelemetry",
                affected_service_name=span.get("service_name"),
                raw_source_ref=f"span:{span.get('span_id')}",
                description=f"{span.get('service_name')} {span.get('operation_name')} failed ({span.get('duration_ms')}ms)",
                relevant_observation=f"HTTP {span.get('status_code')} with duration {span.get('duration_ms')}ms",
                confidence_score=0.98,
                is_contradictory=False,
                verification_status="VERIFIED",
            )
            session.add(ev)
            exhibits.append(ev)

        await session.flush()
        return exhibits

    async def _persist_hypothesis(
        self,
        incident_id: str,
        hyp_dict: Dict[str, Any],
        confidence: float,
        status: str,
        ruling: str,
        session: AsyncSession,
    ):
        culprit_name = hyp_dict.get("culprit_service")
        svc_stmt = select(Service).where(Service.name == culprit_name)
        svc_res = await session.execute(svc_stmt)
        svc = svc_res.scalar_one_or_none()

        hyp = RootCauseHypothesis(
            incident_id=incident_id,
            culprit_service_id=svc.id if svc else None,
            hypothesis_text=hyp_dict.get("hypothesis_text", ""),
            probability_score=confidence,
            status=status,
            prosecutor_argument=hyp_dict.get("prosecutor_argument"),
            defense_argument=hyp_dict.get("defense_argument"),
            judicial_ruling=ruling,
            causal_chain=hyp_dict.get("causal_mechanism"),
            is_confirmed_root_cause=(status == "VALIDATED"),
        )
        session.add(hyp)
        await session.flush()
