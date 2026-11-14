"""
INCIDENTX AI - Explainable Confidence Scoring Engine (Phase 11 Module 11.5)
Calculates deterministic, mathematical confidence scores based on empirical facts,
evidence independence across distinct domains, temporal sequence alignment,
counter-evidence penalties, and missing evidence gap deductions.
"""

from typing import Any, Dict, List, Tuple
from backend.app.core.logging import logger
from backend.app.services.root_cause.schemas import (
    ConfidenceCategory,
    HypothesisItem,
    HypothesisStatus,
)


class ConfidenceScorer:
    """
    Deterministic & Explainable Confidence Scorer.
    Zero hallucinated certainty; full mathematical transparency.
    """

    # Scoring Weights
    W_FACTS = 0.30       # Empirical Fact Ratio
    W_DIVERSITY = 0.25   # Domain Independence (cross-plane coverage)
    W_TEMPORAL = 0.20    # Causal Temporal Ordering
    W_CONTRA = 0.35      # Counter-evidence deduction
    W_GAPS = 0.15        # Missing critical evidence deduction
    BASE_PRIOR = 0.30    # Default neutral prior

    @classmethod
    def categorize_score(cls, score: float) -> ConfidenceCategory:
        if score >= 0.85:
            return ConfidenceCategory.VERY_HIGH
        if score >= 0.70:
            return ConfidenceCategory.HIGH
        if score >= 0.50:
            return ConfidenceCategory.MODERATE
        if score >= 0.25:
            return ConfidenceCategory.LOW
        return ConfidenceCategory.INSUFFICIENT_EVIDENCE

    @classmethod
    def score_hypothesis(
        cls,
        hypothesis: HypothesisItem,
        correlated_data: Dict[str, Any],
    ) -> Tuple[float, ConfidenceCategory, Dict[str, Any], str]:
        """
        Computes the deterministic score and returns the category, breakdown, and explanation.
        """
        facts = correlated_data.get("facts", [])
        total_facts = len(facts)
        supp_ids = set(hypothesis.supporting_evidence_ids)
        contra_ids = set(hypothesis.contradicting_evidence_ids)

        # 1. Empirical Fact Ratio (how many supporting items are verified ground facts)
        supporting_facts = [f for f in facts if f.id in supp_ids]
        fact_ratio = len(supporting_facts) / max(1, len(supp_ids)) if supp_ids else 0.0

        # 2. Domain Diversity (independent signals: K8s, Logs, Metrics, Network, etc.)
        distinct_domains = set(hypothesis.source_domains)
        domain_coverage = min(1.0, len(distinct_domains) / 3.0)  # Max out at 3 independent domains

        # 3. Temporal Alignment (did triggering event precede symptoms?)
        temporal_score = 0.85 if hypothesis.triggering_event else 0.40

        # 4. Counter-Evidence Factor
        contra_count = len(contra_ids)
        contra_factor = min(1.0, contra_count * 0.50)

        # 5. Missing Evidence Factor
        gap_count = len(hypothesis.missing_evidence)
        gap_factor = min(1.0, gap_count * 0.30)

        # Compute raw score
        raw_score = (
            cls.BASE_PRIOR
            + (cls.W_FACTS * fact_ratio)
            + (cls.W_DIVERSITY * domain_coverage)
            + (cls.W_TEMPORAL * temporal_score)
            - (cls.W_CONTRA * contra_factor)
            - (cls.W_GAPS * gap_factor)
        )

        final_score = max(0.05, min(0.96, round(raw_score, 2)))
        category = cls.categorize_score(final_score)

        # If contradicted or rejected, cap category
        if hypothesis.status in (HypothesisStatus.CONTRADICTED, HypothesisStatus.REJECTED):
            final_score = min(final_score, 0.20)
            category = ConfidenceCategory.INSUFFICIENT_EVIDENCE

        breakdown = {
            "base_prior": cls.BASE_PRIOR,
            "fact_ratio": round(fact_ratio, 2),
            "fact_contribution": round(cls.W_FACTS * fact_ratio, 3),
            "domain_coverage": round(domain_coverage, 2),
            "diversity_contribution": round(cls.W_DIVERSITY * domain_coverage, 3),
            "temporal_alignment": round(temporal_score, 2),
            "temporal_contribution": round(cls.W_TEMPORAL * temporal_score, 3),
            "contra_deduction": round(cls.W_CONTRA * contra_factor, 3),
            "gap_deduction": round(cls.W_GAPS * gap_factor, 3),
            "final_score": final_score,
            "category": category.value,
        }

        explanation = (
            f"Confidence Score {final_score:.2f} ({category.value}): "
            f"Empirical fact coverage {fact_ratio*100:.0f}% across {len(distinct_domains)} independent domains. "
            f"Temporal alignment score: {temporal_score:.2f}. "
            f"Deductions applied: -{breakdown['contra_deduction']:.2f} for {contra_count} counter-evidence exhibits, "
            f"-{breakdown['gap_deduction']:.2f} for {gap_count} unverified evidence gaps."
        )

        return final_score, category, breakdown, explanation


confidence_scorer = ConfidenceScorer()
