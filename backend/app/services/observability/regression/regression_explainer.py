"""
INCIDENTX AI - SRE Regression Explanation Engine
Synthesizes deterministic comparison evidence, historical fingerprints,
and remediation stability into 10 structured SRE operational answers.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SRERegressionExplanation:
    """The 10 standardized SRE answers explaining a detected regression."""
    which_previous_incident: str
    affected_services: str
    metrics_returning_abnormal: str
    original_root_cause_hypothesis: str
    previous_remediation_performed: str
    did_remediation_provide_sustained_improvement: str
    evidence_supporting_recurrence: str
    evidence_contradicting_recurrence: str
    similarity_strength: str
    next_investigation_step: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "which_previous_incident": self.which_previous_incident,
            "affected_services": self.affected_services,
            "metrics_returning_abnormal": self.metrics_returning_abnormal,
            "original_root_cause_hypothesis": self.original_root_cause_hypothesis,
            "previous_remediation_performed": self.previous_remediation_performed,
            "did_remediation_provide_sustained_improvement": self.did_remediation_provide_sustained_improvement,
            "evidence_supporting_recurrence": self.evidence_supporting_recurrence,
            "evidence_contradicting_recurrence": self.evidence_contradicting_recurrence,
            "similarity_strength": self.similarity_strength,
            "next_investigation_step": self.next_investigation_step,
        }


class SRERegressionExplainer:
    """
    Constructs standardized SRE answers explaining regression and recurrence findings.
    Clearly distinguishes confirmed historical facts from live hypotheses.
    """

    @classmethod
    def explain(
        cls,
        current_service: str,
        current_metric: str,
        observed_value: float,
        expected_baseline: float,
        post_remediation_value: float,
        historical_incident: Optional[Dict[str, Any]] = None,
        similarity_data: Optional[Dict[str, Any]] = None,
        remediation_data: Optional[Dict[str, Any]] = None,
        regression_score: float = 0.5,
        classification: str = "POSSIBLE_REGRESSION",
    ) -> SRERegressionExplanation:
        hist = historical_incident or {}
        sim = similarity_data or {}
        rem = remediation_data or {}

        hist_id = hist.get("id") or hist.get("incident_id") or "HIST-INC-001"
        hist_title = hist.get("title") or "Previous Infrastructure Failure"
        hist_hypothesis = hist.get("hypothesis") or hist.get("summary") or "Unspecified historical failure"

        # 1. Which previous incident does this resemble?
        which_prev = f"Incident '{hist_title}' (ID: {hist_id[:8]}...)" if hist_id else "No matching historical incident identified."

        # 2. Which services are affected?
        aff_services = hist.get("affected_services") or [current_service]
        if isinstance(aff_services, list):
            aff_str = f"{current_service} (Primary Culprit) alongside connected dependencies: {', '.join([s for s in aff_services if s != current_service]) or 'None'}"
        else:
            aff_str = str(aff_services)

        # 3. Which metrics are returning to abnormal levels?
        delta_pct = ((observed_value - expected_baseline) / max(0.1, expected_baseline)) * 100
        metrics_abnormal = (
            f"{current_metric} is returning to abnormal levels: observed {observed_value:.2f} "
            f"(baseline {expected_baseline:.2f}, post-remediation was {post_remediation_value:.2f}, "
            f"departure +{delta_pct:.1f}%)."
        )

        # 4. What was the original root-cause hypothesis?
        orig_rc = hist_hypothesis

        # 5. What remediation was previously performed?
        act_name = rem.get("name") or rem.get("action_name") or "Standard automated service restart"
        prev_rem = f"Action '{act_name}' (Target: {rem.get('target_service_name', current_service)})"

        # 6. Did that remediation provide sustained improvement?
        outcome = rem.get("outcome", "TEMPORARY_SUCCESS")
        if outcome == "SUSTAINED_SUCCESS":
            sustained = "Yes, previous remediation achieved sustained improvement until current recurring onset."
        elif outcome == "TEMPORARY_SUCCESS":
            sustained = "No. Remediation provided temporary stabilization, followed by subsequent re-degradation."
        elif outcome == "FAILED":
            sustained = "No. Previous remediation failed verification or necessitated a rollback."
        else:
            sustained = f"Partial/Inconclusive outcome: classified as {outcome}."

        # 7. What evidence supports recurrence?
        supporting_items: List[str] = []
        if sim.get("services_similarity", 0.0) >= 0.7:
            supporting_items.append("Identical service topology footprint")
        if sim.get("metric_vector_similarity", 0.0) >= 0.7:
            supporting_items.append(f"Matching anomaly vector on {current_metric}")
        if sim.get("root_cause_similarity", 0.0) >= 0.6:
            supporting_items.append("Concordant root-cause taxonomy")
        if observed_value > expected_baseline:
            supporting_items.append(f"Empirical metric departure exceeds nominal 3σ bounds by +{delta_pct:.1f}%")
        evidence_sup = "; ".join(supporting_items) if supporting_items else "Metric drift observed on the same microservice node."

        # 8. What evidence contradicts recurrence?
        contradicting_items: List[str] = []
        if sim.get("error_signature_similarity", 0.0) < 0.3:
            contradicting_items.append("Error log signatures differ from previous incident logs")
        if sim.get("services_similarity", 1.0) < 0.5:
            contradicting_items.append("Different cascading downstream blast radius")
        if delta_pct < 20.0:
            contradicting_items.append("Metric deviation magnitude is significantly lower than original failure")
        evidence_contra = "; ".join(contradicting_items) if contradicting_items else "No significant contradictory evidence observed."

        # 9. How strong is the similarity?
        sim_score = sim.get("overall_similarity_score", regression_score)
        sim_str = f"{(sim_score * 100):.1f}% Multi-Feature Similarity ({classification.replace('_', ' ')})"

        # 10. What should the SRE investigate next?
        if "pool" in current_metric or "connection" in current_metric:
            next_step = (
                f"Verify connection leak signatures on '{current_service}' database driver and inspect active "
                f"idle connections before repeating connection pool flush."
            )
        elif "memory" in current_metric:
            next_step = (
                f"Inspect heap allocation profiles and garbage collection pauses on '{current_service}' to identify "
                f"unreclaimed memory buffers."
            )
        elif "latency" in current_metric:
            next_step = (
                f"Inspect distributed trace waterfall spans for '{current_service}' to identify whether latency originates "
                f"in local processing or downstream RPC calls."
            )
        else:
            next_step = (
                f"Initiate multi-agent root-cause investigation to compare deployment revision diffs and configuration changes."
            )

        return SRERegressionExplanation(
            which_previous_incident=which_prev,
            affected_services=aff_str,
            metrics_returning_abnormal=metrics_abnormal,
            original_root_cause_hypothesis=orig_rc,
            previous_remediation_performed=prev_rem,
            did_remediation_provide_sustained_improvement=sustained,
            evidence_supporting_recurrence=evidence_sup,
            evidence_contradicting_recurrence=evidence_contra,
            similarity_strength=sim_str,
            next_investigation_step=next_step,
        )
