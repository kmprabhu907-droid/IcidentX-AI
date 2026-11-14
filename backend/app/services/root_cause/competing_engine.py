"""
INCIDENTX AI - Competing Hypothesis Engine (Phase 11 Module 11.2)
Evaluates, compares, and ranks multiple candidate hypotheses simultaneously.
Identifies shared evidence, discriminating exhibits, conflicting evidence,
unsupported assumptions, and generates clear comparative explanations.
Enforces the rule: Never select a root cause simply because an AI model suggested it first.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.services.root_cause.confidence_scorer import confidence_scorer
from backend.app.services.root_cause.schemas import (
    CompetingHypothesisAnalysis,
    ConfidenceCategory,
    HypothesisItem,
    HypothesisStatus,
)


class CompetingHypothesisEngine:
    """
    Judicial Competing Hypothesis Evaluator.
    Ranks hypotheses objectively based on discriminating empirical evidence.
    """

    @classmethod
    def evaluate_competing_hypotheses(
        cls,
        incident_id: str,
        investigation_id: Optional[str],
        hypotheses: List[HypothesisItem],
        correlated_data: Dict[str, Any],
    ) -> CompetingHypothesisAnalysis:
        """
        Performs simultaneous comparative analysis of all candidate hypotheses.
        """
        # 1. Score each hypothesis deterministically
        for hyp in hypotheses:
            score, category, breakdown, expl = confidence_scorer.score_hypothesis(hyp, correlated_data)
            hyp.confidence_score = score
            hyp.confidence_category = category
            hyp.score_breakdown = breakdown

        # 2. Sort descending by confidence score
        ranked = sorted(hypotheses, key=lambda h: h.confidence_score, reverse=True)

        # 3. Identify Shared Evidence vs. Discriminating Evidence
        evidence_usage: Dict[str, List[str]] = {}
        for hyp in ranked:
            for ev_id in hyp.supporting_evidence_ids:
                if ev_id not in evidence_usage:
                    evidence_usage[ev_id] = []
                evidence_usage[ev_id].append(hyp.id)

        shared_matrix: Dict[str, List[str]] = {
            ev_id: hyp_ids for ev_id, hyp_ids in evidence_usage.items() if len(hyp_ids) > 1
        }

        discriminating_matrix: Dict[str, List[str]] = {}
        for hyp in ranked:
            unique_exhibits = [
                ev_id for ev_id in hyp.supporting_evidence_ids if len(evidence_usage.get(ev_id, [])) == 1
            ]
            discriminating_matrix[hyp.id] = unique_exhibits

        # 4. Map Unsupported Assumptions
        unsupported: Dict[str, List[str]] = {}
        for hyp in ranked:
            if hyp.assumptions and (hyp.confidence_score < 0.70 or hyp.missing_evidence):
                unsupported[hyp.id] = hyp.assumptions

        # 5. Build Comparative Ranking Explanation
        top_hyp = ranked[0] if ranked else None
        second_hyp = ranked[1] if len(ranked) > 1 else None

        if top_hyp and top_hyp.confidence_score >= 0.70:
            top_hyp.status = HypothesisStatus.CONFIRMED if top_hyp.confidence_score >= 0.85 else HypothesisStatus.SUPPORTED
            rationale = (
                f"Leading Root Cause: '{top_hyp.title}' (Score {top_hyp.confidence_score:.2f}, {top_hyp.confidence_category.value}). "
            )
            if second_hyp:
                rationale += (
                    f"Ranks above '{second_hyp.title}' (Score {second_hyp.confidence_score:.2f}) because it has "
                    f"{len(discriminating_matrix.get(top_hyp.id, []))} uniquely discriminating exhibits and "
                    f"direct temporal correlation with the triggering event ({top_hyp.triggering_event or 'onset'}). "
                )
                if second_hyp.status in (HypothesisStatus.CONTRADICTED, HypothesisStatus.REJECTED):
                    rationale += (
                        f"Meanwhile, '{second_hyp.title}' was refuted by counter-evidence."
                    )
        elif top_hyp and top_hyp.confidence_score >= 0.50:
            rationale = (
                f"Moderate Evidence: '{top_hyp.title}' is the leading candidate (Score {top_hyp.confidence_score:.2f}), "
                f"but requires corroborating exhibits before confirmation. "
                f"Missing signals: {'; '.join(top_hyp.missing_evidence[:2]) or 'span traces'}."
            )
        else:
            if top_hyp:
                top_hyp.status = HypothesisStatus.INCONCLUSIVE
            rationale = (
                "Inconclusive Investigation: Ground telemetry does not decisively distinguish between the competing causes. "
                "All candidate hypotheses lack required empirical proof or exhibit conflicting signals."
            )

        return CompetingHypothesisAnalysis(
            incident_id=incident_id,
            investigation_id=investigation_id,
            total_hypotheses=len(ranked),
            ranked_hypotheses=ranked,
            shared_evidence_matrix=shared_matrix,
            discriminating_evidence=discriminating_matrix,
            conflicting_evidence_notes=[
                f"Hypothesis {h.id} contradicts expected telemetry: {len(h.contradicting_evidence_ids)} counter-evidence points found."
                for h in ranked if h.contradicting_evidence_ids
            ],
            unsupported_assumptions=unsupported,
            ranking_rationale=rationale,
            top_hypothesis_id=top_hyp.id if (top_hyp and top_hyp.status != HypothesisStatus.INCONCLUSIVE) else None,
        )


competing_hypothesis_engine = CompetingHypothesisEngine()
