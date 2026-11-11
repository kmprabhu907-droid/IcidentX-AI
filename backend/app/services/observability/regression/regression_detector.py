"""
INCIDENTX AI - Core Regression Detection Engine
Detects 7 regression and recurrence failure patterns:
  1. Same failure recurring after recovery
  2. Previously resolved metric becoming abnormal again
  3. Gradual post-remediation degradation (creeping resource return)
  4. Repeated failure in the same dependency
  5. Remediation providing only temporary improvement
  6. Failed remediation strategies recurring
  7. New failures caused by secondary service degradation

Computes an explainable composite regression score and deterministic classification:
  CONFIRMED_REGRESSION (>= 0.80 + deterministic evidence)
  LIKELY_REGRESSION (>= 0.65)
  POSSIBLE_REGRESSION (>= 0.45)
  LOW_SIMILARITY (< 0.45)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.services.observability.regression.comparison_engine import (
    FourStateComparison,
    FourStateComparisonEngine,
    SIGNAL_SPECIFICATIONS,
)
from backend.app.services.observability.regression.fingerprint import (
    FingerprintBuilder,
    IncidentFingerprint,
)
from backend.app.services.observability.regression.remediation_effectiveness import (
    RemediationEffectivenessAnalyzer,
    RemediationEffectivenessReport,
)
from backend.app.services.observability.regression.regression_explainer import (
    SRERegressionExplainer,
    SRERegressionExplanation,
)
from backend.app.services.observability.regression.similarity import (
    IncidentSimilarityEngine,
    SimilarityResult,
)


@dataclass
class RegressionCandidate:
    """Represents a fully evaluated and classified regression finding."""
    service_name: str
    metric_name: str
    observed_value: float
    expected_baseline: float
    pre_incident_value: Optional[float]
    post_remediation_value: float
    regression_score: float
    similarity_score: float
    classification: str  # LOW_SIMILARITY, POSSIBLE_REGRESSION, LIKELY_REGRESSION, CONFIRMED_REGRESSION
    detected_pattern: str  # One of the 7 regression pattern names
    original_incident_id: str
    current_incident_id: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    matching_incident_ids: List[str] = field(default_factory=list)
    previous_remediation_ids: List[str] = field(default_factory=list)
    comparison: Optional[FourStateComparison] = None
    similarity_result: Optional[SimilarityResult] = None
    remediation_report: Optional[RemediationEffectivenessReport] = None
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    explanation: Optional[SRERegressionExplanation] = None
    data_source: str = "SIMULATED"
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "observed_value": round(self.observed_value, 2),
            "expected_baseline": round(self.expected_baseline, 2),
            "pre_incident_value": round(self.pre_incident_value, 2) if self.pre_incident_value is not None else None,
            "post_remediation_value": round(self.post_remediation_value, 2),
            "regression_score": round(self.regression_score, 3),
            "similarity_score": round(self.similarity_score, 3),
            "classification": self.classification,
            "detected_pattern": self.detected_pattern,
            "original_incident_id": self.original_incident_id,
            "current_incident_id": self.current_incident_id,
            "affected_services": self.affected_services,
            "matching_incident_ids": self.matching_incident_ids,
            "previous_remediation_ids": self.previous_remediation_ids,
            "score_breakdown": self.score_breakdown,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "similarity_result": self.similarity_result.to_dict() if self.similarity_result else None,
            "remediation_report": self.remediation_report.to_dict() if self.remediation_report else None,
            "explanation": self.explanation.to_dict() if self.explanation else None,
            "data_source": self.data_source,
            "detected_at": self.detected_at.isoformat(),
        }


class UnifiedRegressionDetector:
    """
    Main Regression Detection Engine.
    Correlates current active anomalies and telemetry with historical incident fingerprints,
    four-state comparison deltas, and Phase 4 remediation verification records.
    """

    @classmethod
    def evaluate_service_regression(
        cls,
        service_name: str,
        current_telemetry: Dict[str, float],
        healthy_baseline: Dict[str, float],
        historical_incident: Dict[str, Any],
        historical_fingerprint: Optional[IncidentFingerprint] = None,
        pre_incident_telemetry: Optional[Dict[str, float]] = None,
        post_remediation_telemetry: Optional[Dict[str, float]] = None,
        remediation_action: Optional[Dict[str, Any]] = None,
        historical_samples: Optional[List[Dict[str, Any]]] = None,
        data_source: str = "SIMULATED",
    ) -> List[RegressionCandidate]:
        """
        Evaluates whether current telemetry represents a regression of the historical incident.
        """
        candidates: List[RegressionCandidate] = []

        pre_telemetry = pre_incident_telemetry or {}
        post_telemetry = post_remediation_telemetry or {}

        # 1. Execute Four-State Comparison Engine
        comparison = FourStateComparisonEngine.compare(
            service_name=service_name,
            healthy_baseline=healthy_baseline,
            pre_incident=pre_telemetry,
            post_remediation=post_telemetry,
            current_state=current_telemetry,
        )

        # 2. Build live incident fingerprint for the current telemetry
        current_anomalies: Dict[str, float] = {}
        for m_name, mv in comparison.metrics.items():
            if mv.is_regressing:
                current_anomalies[m_name] = abs(mv.delta_total_departure)

        live_fp = FingerprintBuilder.build(
            incident_id="live-eval",
            primary_service=service_name,
            affected_services=[service_name] + [
                m for m in comparison.regressing_metrics
            ],
            telemetry_anomalies=current_anomalies,
            hypotheses=[historical_incident.get("summary", "")],
        )

        # 3. Calculate Fingerprint Similarity if historical fingerprint exists
        sim_result: Optional[SimilarityResult] = None
        if historical_fingerprint:
            sim_result = IncidentSimilarityEngine.compare_fingerprints(
                live_fp, historical_fingerprint
            )
        else:
            # Construct minimal historical fingerprint from incident dict
            hist_fp = FingerprintBuilder.build(
                incident_id=historical_incident.get("id", "hist-0"),
                primary_service=historical_incident.get("impact_scope", service_name).split(",")[0].strip(),
                telemetry_anomalies={k: abs(v - healthy_baseline.get(k, v)) for k, v in pre_telemetry.items()},
                hypotheses=[historical_incident.get("summary", "")],
            )
            sim_result = IncidentSimilarityEngine.compare_fingerprints(live_fp, hist_fp)

        # 4. Evaluate Remediation Effectiveness if remediation action exists
        rem_report: Optional[RemediationEffectivenessReport] = None
        if remediation_action:
            rem_report = RemediationEffectivenessAnalyzer.evaluate(
                action_dict=remediation_action,
                historical_samples=historical_samples or [],
                current_telemetry=current_telemetry,
                healthy_baseline=healthy_baseline,
            )

        # 5. For each regressing metric, evaluate the 7 patterns and formulate candidates
        for metric_name in comparison.regressing_metrics:
            mv = comparison.metrics[metric_name]
            obs_val = mv.current_state
            base_val = mv.healthy_baseline
            post_val = mv.post_remediation
            pre_val = mv.pre_incident

            # Determine which of the 7 regression patterns applies
            pattern = cls._determine_pattern(
                metric_name=metric_name,
                mv=mv,
                service_name=service_name,
                historical_incident=historical_incident,
                rem_report=rem_report,
                sim_result=sim_result,
            )

            # Compute Explainable Composite Regression Score
            score, breakdown = cls._calculate_regression_score(
                mv=mv,
                sim_result=sim_result,
                rem_report=rem_report,
                pattern=pattern,
            )

            # Classify Deterministically
            classification = cls._classify_regression(
                score=score,
                pattern=pattern,
                sim_result=sim_result,
                service_name=service_name,
                historical_incident=historical_incident,
            )

            # Generate 10 SRE Diagnostic Answers
            explanation = SRERegressionExplainer.explain(
                current_service=service_name,
                current_metric=metric_name,
                observed_value=obs_val,
                expected_baseline=base_val,
                post_remediation_value=post_val,
                historical_incident=historical_incident,
                similarity_data=sim_result.to_dict() if sim_result else {},
                remediation_data=remediation_action or {},
                regression_score=score,
                classification=classification,
            )

            candidate = RegressionCandidate(
                service_name=service_name,
                metric_name=metric_name,
                observed_value=obs_val,
                expected_baseline=base_val,
                pre_incident_value=pre_val,
                post_remediation_value=post_val,
                regression_score=score,
                similarity_score=sim_result.overall_similarity_score if sim_result else 0.0,
                classification=classification,
                detected_pattern=pattern,
                original_incident_id=historical_incident.get("id", "HIST-0"),
                current_incident_id=None,
                affected_services=list(live_fp.affected_services),
                matching_incident_ids=[historical_incident.get("id", "")],
                previous_remediation_ids=[remediation_action["id"]] if (remediation_action and "id" in remediation_action) else [],
                comparison=comparison,
                similarity_result=sim_result,
                remediation_report=rem_report,
                score_breakdown=breakdown,
                explanation=explanation,
                data_source=data_source,
            )
            candidates.append(candidate)

        return candidates

    @classmethod
    def _determine_pattern(
        cls,
        metric_name: str,
        mv: Any,
        service_name: str,
        historical_incident: Dict[str, Any],
        rem_report: Optional[RemediationEffectivenessReport],
        sim_result: Optional[SimilarityResult],
    ) -> str:
        """Determines which of the 7 regression failure patterns is manifested."""
        # Pattern 5: Remediation provided only temporary improvement
        if rem_report and rem_report.outcome == "TEMPORARY_SUCCESS":
            return "TEMPORARY_REMEDIATION_IMPROVEMENT"

        # Pattern 6: Failed remediation strategies recurring / rollback required
        if rem_report and (rem_report.outcome == "FAILED" or rem_report.required_rollback):
            return "FAILED_STRATEGY_RECURRING"

        # Pattern 4: Repeated failure in the same dependency (e.g. database pool)
        if metric_name in ["db_pool_utilization", "dependency_health"] or "postgres" in service_name:
            return "REPEATED_DEPENDENCY_FAILURE"

        # Pattern 3: Gradual post-remediation degradation (creeping memory or pool)
        if metric_name in ["memory_utilization", "disk_utilization"] and mv.delta_degradation > 0:
            return "GRADUAL_POST_REMEDIATION_DEGRADATION"

        # Pattern 7: Secondary service degradation
        if rem_report and rem_report.outcome == "PARTIAL_SUCCESS" and metric_name in rem_report.secondary_degraded_metrics:
            return "SECONDARY_SERVICE_DEGRADATION"

        # Pattern 1: Same failure recurring after recovery
        if sim_result and sim_result.overall_similarity_score >= 0.70:
            return "SAME_FAILURE_RECURRING"

        # Pattern 2: Previously resolved metric becoming abnormal again
        return "RESOLVED_METRIC_RE-ABNORMAL"

    @classmethod
    def _calculate_regression_score(
        cls,
        mv: Any,
        sim_result: Optional[SimilarityResult],
        rem_report: Optional[RemediationEffectivenessReport],
        pattern: str,
    ) -> tuple[float, Dict[str, float]]:
        """
        Calculates composite regression score in [0.0, 1.0].
        Weights:
          Fingerprint similarity: 0.30
          Metric departure magnitude: 0.25
          Post-remediation degradation delta: 0.20
          Pattern severity weight: 0.15
          Stability failure weight: 0.10
        """
        sim_score = sim_result.overall_similarity_score if sim_result else 0.40

        # Metric departure magnitude relative to baseline
        base = max(0.1, abs(mv.healthy_baseline))
        dep_ratio = min(1.0, abs(mv.delta_total_departure) / (base * 1.5))

        # Degradation since remediation (1.0 = full regression back to pre-incident level)
        recovery_mag = max(0.1, abs(mv.delta_recovery))
        deg_score = min(1.0, max(0.0, abs(mv.delta_degradation) / recovery_mag))

        # Pattern weight
        pattern_weights = {
            "SAME_FAILURE_RECURRING": 0.95,
            "REPEATED_DEPENDENCY_FAILURE": 0.90,
            "TEMPORARY_REMEDIATION_IMPROVEMENT": 0.85,
            "FAILED_STRATEGY_RECURRING": 0.85,
            "RESOLVED_METRIC_RE-ABNORMAL": 0.80,
            "GRADUAL_POST_REMEDIATION_DEGRADATION": 0.75,
            "SECONDARY_SERVICE_DEGRADATION": 0.70,
        }
        pat_score = pattern_weights.get(pattern, 0.60)

        # Stability failure weight from remediation effectiveness
        if rem_report:
            stab_fail_score = 1.0 - rem_report.stability_score
        else:
            stab_fail_score = 0.50

        # Composite score
        total_score = (
            0.30 * sim_score
            + 0.25 * dep_ratio
            + 0.20 * deg_score
            + 0.15 * pat_score
            + 0.10 * stab_fail_score
        )
        total_score = max(0.0, min(1.0, total_score))

        breakdown = {
            "fingerprint_similarity_component": round(0.30 * sim_score, 3),
            "departure_magnitude_component": round(0.25 * dep_ratio, 3),
            "degradation_since_recovery_component": round(0.20 * deg_score, 3),
            "pattern_severity_component": round(0.15 * pat_score, 3),
            "stability_failure_component": round(0.10 * stab_fail_score, 3),
        }

        return round(total_score, 3), breakdown

    @classmethod
    def _classify_regression(
        cls,
        score: float,
        pattern: str,
        sim_result: Optional[SimilarityResult],
        service_name: str,
        historical_incident: Dict[str, Any],
    ) -> str:
        """
        Deterministic classification:
        CONFIRMED_REGRESSION requires score >= 0.80 AND deterministic evidence:
          - High similarity (>= 0.70)
          - Clear matching pattern
          - Matching primary culprit
        """
        has_deterministic_evidence = (
            sim_result is not None
            and sim_result.overall_similarity_score >= 0.70
            and pattern in [
                "SAME_FAILURE_RECURRING",
                "REPEATED_DEPENDENCY_FAILURE",
                "TEMPORARY_REMEDIATION_IMPROVEMENT",
                "FAILED_STRATEGY_RECURRING",
                "RESOLVED_METRIC_RE-ABNORMAL",
            ]
        )

        if score >= 0.80 and has_deterministic_evidence:
            return "CONFIRMED_REGRESSION"
        elif score >= 0.65:
            return "LIKELY_REGRESSION"
        elif score >= 0.45:
            return "POSSIBLE_REGRESSION"
        else:
            return "LOW_SIMILARITY"
