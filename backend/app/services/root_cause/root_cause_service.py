"""
INCIDENTX AI - Root Cause Intelligence Service (Phase 11 Module 11.9)
Unified enterprise coordinator integrating:
- Multi-domain Evidence Correlation (Module 11.3)
- Intelligent Hypothesis Generation (Module 11.1)
- Active Counter-Evidence Disproof (Module 11.4)
- Explainable Confidence Scoring (Module 11.5)
- Simultaneous Competing Hypothesis Ranking (Module 11.2)
- Causal Graph Synthesis (Module 11.6)
- Historical Incident Intelligence & Recurrence Detection (Module 11.7)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.investigation import RootCauseHypothesis
from backend.app.services.root_cause.causal_engine import causal_reasoning_engine
from backend.app.services.root_cause.competing_engine import competing_hypothesis_engine
from backend.app.services.root_cause.confidence_scorer import confidence_scorer
from backend.app.services.root_cause.counter_evidence_engine import counter_evidence_engine
from backend.app.services.root_cause.evidence_correlator import evidence_correlator
from backend.app.services.root_cause.historical_intelligence import historical_incident_intelligence
from backend.app.services.root_cause.hypothesis_generator import hypothesis_generator
from backend.app.services.root_cause.schemas import (
    CausalGraph,
    CompetingHypothesisAnalysis,
    CounterEvidenceReport,
    HypothesisItem,
    HypothesisStatus,
    RootCauseReport,
    SimilarIncidentMatch,
)


class RootCauseIntelligenceService:
    """
    Master Service for Phase 11 Root Cause Intelligence.
    Coordinates the full cycle: Correlate -> Generate -> Disprove -> Score -> Compete -> Graph -> Report.
    """

    @classmethod
    async def evaluate_incident_root_cause(
        cls,
        incident_id: str,
        session: AsyncSession,
        investigation_id: Optional[str] = None,
        affected_service: Optional[str] = None,
    ) -> RootCauseReport:
        """
        Executes the end-to-end Root Cause Intelligence evaluation for an incident.
        """
        logger.info(f"[RootCauseService] Evaluating Root Cause Intelligence for incident {incident_id}")

        # 1. Fetch Incident context
        inc_stmt = select(Incident).where(Incident.id == incident_id)
        inc_res = await session.execute(inc_stmt)
        incident = inc_res.scalar_one_or_none()

        target_service = affected_service or (incident.impact_scope if incident else "cluster")
        inv_id = investigation_id or f"inv-{uuid.uuid4().hex[:8]}"

        # 2. Correlate Evidence across all planes (Module 11.3)
        correlated = await evidence_correlator.correlate_incident_evidence(
            incident_id=incident_id,
            session=session,
            affected_service=target_service,
        )

        # 3. Generate Multiple Competing Hypotheses (Module 11.1)
        hypotheses = hypothesis_generator.generate_hypotheses(
            incident_id=incident_id,
            investigation_id=inv_id,
            correlated_data=correlated,
            affected_service=target_service,
        )

        # 4. Active Counter-Evidence Disproof (Module 11.4)
        counter_reports = counter_evidence_engine.evaluate_counter_evidence(
            hypotheses=hypotheses,
            correlated_data=correlated,
        )

        # 5. Simultaneous Competing Hypothesis Ranking (Module 11.2 & 11.5)
        competing_analysis = competing_hypothesis_engine.evaluate_competing_hypotheses(
            incident_id=incident_id,
            investigation_id=inv_id,
            hypotheses=hypotheses,
            correlated_data=correlated,
        )

        ranked = competing_analysis.ranked_hypotheses
        top_hypothesis = ranked[0] if ranked else hypotheses[0]

        # 6. Causal Graph Synthesis (Module 11.6)
        causal_graph = causal_reasoning_engine.build_causal_graph(
            incident_id=incident_id,
            leading_hypothesis=top_hypothesis,
            correlated_data=correlated,
        )

        # 7. Historical Incident Intelligence & Recurrence (Module 11.7)
        similar_matches = await historical_incident_intelligence.find_similar_incidents(
            incident_id=incident_id,
            session=session,
            limit=5,
        )
        is_recurrent = len(similar_matches) >= 1 and similar_matches[0].similarity_score >= 0.70

        # 8. Persist Leading Hypotheses to database for backward compatibility with Phase 3-10
        for hyp in ranked:
            db_hyp = RootCauseHypothesis(
                id=hyp.id,
                incident_id=incident_id,
                culprit_service_id=None,
                hypothesis_text=hyp.description,
                probability_score=hyp.confidence_score,
                status=(
                    "VALIDATED" if hyp.status in (HypothesisStatus.CONFIRMED, HypothesisStatus.SUPPORTED)
                    else "DISPROVEN" if hyp.status in (HypothesisStatus.CONTRADICTED, HypothesisStatus.REJECTED)
                    else "INSUFFICIENT_EVIDENCE"
                ),
                prosecutor_argument=f"Supported by {len(hyp.supporting_evidence_ids)} exhibits across {', '.join(hyp.source_domains)}.",
                defense_argument=(
                    f"Contradicted by {len(hyp.contradicting_evidence_ids)} counter-evidence signals."
                    if hyp.contradicting_evidence_ids else "No direct counter-evidence found."
                ),
                judicial_ruling=f"Ranked confidence {hyp.confidence_score:.2f} ({hyp.confidence_category.value}).",
                causal_chain=hyp.causal_chain_summary,
                missing_evidence="; ".join(hyp.missing_evidence) if hyp.missing_evidence else None,
                evidence_count=len(hyp.supporting_evidence_ids),
                contradiction_count=len(hyp.contradicting_evidence_ids),
                is_confirmed_root_cause=(hyp.id == top_hypothesis.id and top_hypothesis.confidence_score >= 0.70),
            )
            session.add(db_hyp)
        await session.flush()

        # 9. Executive Postmortem Summary
        summary_text = (
            f"Autonomous Root Cause Intelligence concluded with leading verdict: '{top_hypothesis.title}'. "
            f"Evaluated {len(hypotheses)} competing hypotheses against {correlated['total_evidence_count']} exhibits. "
            f"Active counter-evidence analysis applied {len(counter_reports)} disproof assessments. "
            f"Confidence: {top_hypothesis.confidence_score:.2f} ({top_hypothesis.confidence_category.value}). "
            f"Causal verification ratio: {causal_graph.verified_causal_ratio*100:.0f}%. "
            f"Historical recurrence status: {'ALERT: Recurrent incident pattern detected' if is_recurrent else 'No recent recurrence detected'}."
        )

        return RootCauseReport(
            incident_id=incident_id,
            investigation_id=inv_id,
            primary_root_cause=top_hypothesis.title,
            primary_hypothesis=top_hypothesis,
            competing_analysis=competing_analysis,
            counter_evidence_reports=counter_reports,
            causal_graph=causal_graph,
            similar_incidents=similar_matches,
            is_recurrence=is_recurrent,
            recurrence_count=len(similar_matches),
            confidence_score=top_hypothesis.confidence_score,
            confidence_category=top_hypothesis.confidence_category,
            executive_summary=summary_text,
        )


root_cause_service = RootCauseIntelligenceService()
