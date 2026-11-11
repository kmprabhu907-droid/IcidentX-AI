"""
INCIDENTX AI - Explainable Anomaly Confidence Scoring Engine
Computes a transparent, auditable confidence score in [0.0, 1.0] based on
deviation magnitude, temporal persistence, baseline variance, trend consistency,
and corroborating multi-signal evidence.
"""

from typing import Any, Dict, Optional


class AnomalyConfidenceCalculator:
    """
    Produces deterministic, explainable confidence scores.
    Exposes sub-score component weights so SREs can inspect the rationale.
    """

    @staticmethod
    def calculate(
        z_score: float,
        consecutive_observations: int,
        baseline_std_dev: float,
        baseline_mean: float,
        trend_r_squared: Optional[float] = None,
        corroborating_signals_count: int = 0,
        sample_count: int = 10,
    ) -> Dict[str, Any]:
        """
        Calculates multi-factor confidence score with explainable breakdown.
        Weights:
        - Magnitude: 0.25
        - Persistence: 0.20
        - Variability: 0.15
        - Trend Consistency: 0.15
        - Corroborating Evidence: 0.15
        - Sample Adequacy: 0.10
        """
        # 1. Magnitude Score (0.0 to 1.0)
        # z-score 3.0 -> 0.6, z-score >= 6.0 -> 1.0
        mag_score = min(1.0, max(0.0, (abs(z_score) - 1.0) / 5.0))

        # 2. Persistence Score (0.0 to 1.0)
        # 1 observation -> 0.3, 5+ observations -> 1.0
        pers_score = min(1.0, max(0.2, consecutive_observations / 5.0))

        # 3. Baseline Variability Score (0.0 to 1.0)
        # Coefficient of variation (CV = std / mean). Low CV -> higher confidence
        cv = baseline_std_dev / max(0.001, abs(baseline_mean))
        var_score = max(0.3, min(1.0, 1.0 - (cv * 0.5)))

        # 4. Trend Consistency Score (0.0 to 1.0)
        # Uses R-squared if available, otherwise defaults to neutral 0.5
        if trend_r_squared is not None:
            trend_score = min(1.0, max(0.0, trend_r_squared))
        else:
            trend_score = 0.5

        # 5. Corroborating Signals Score (0.0 to 1.0)
        # 0 corroborating -> 0.4, 1 -> 0.75, 2+ -> 1.0
        if corroborating_signals_count >= 2:
            corrob_score = 1.0
        elif corroborating_signals_count == 1:
            corrob_score = 0.75
        else:
            corrob_score = 0.4

        # 6. Sample Adequacy Score (0.0 to 1.0)
        sample_score = min(1.0, max(0.3, sample_count / 30.0))

        # Weighted Sum
        total = (
            (mag_score * 0.25)
            + (pers_score * 0.20)
            + (var_score * 0.15)
            + (trend_score * 0.15)
            + (corrob_score * 0.15)
            + (sample_score * 0.10)
        )
        total_confidence = round(min(0.99, max(0.10, total)), 2)

        return {
            "confidence": total_confidence,
            "components": {
                "magnitude_score": round(mag_score, 2),
                "persistence_score": round(pers_score, 2),
                "variability_score": round(var_score, 2),
                "trend_consistency_score": round(trend_score, 2),
                "corroborating_score": round(corrob_score, 2),
                "sample_adequacy_score": round(sample_score, 2),
            },
        }
