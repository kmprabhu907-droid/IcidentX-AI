"""
INCIDENTX AI - Intelligent Risk Assessment Engine (Phase 12 Module 12.3)
Evaluates risks deterministically prior to action approval and execution.
SAFETY INVARIANT: Deterministic policy rules govern execution eligibility.
AI models CANNOT override safety policies.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.services.resolution.action_library import action_library
from backend.app.services.resolution.schemas import (
    ResolutionActionItem,
    RiskAssessment,
    RiskClassification,
)


class IntelligentRiskEngine:
    """
    Deterministic Safety & Risk Evaluator.
    Considers severity, criticality, blast radius, reversibility, and data integrity.
    """

    CRITICAL_SERVICES = {"payment-service", "auth-service", "checkout-service", "order-service"}
    MODERATE_SERVICES = {"inventory-service", "cart-service", "shipping-service"}

    @classmethod
    def evaluate_action_risk(
        cls,
        plan_id: str,
        action: ResolutionActionItem,
        incident_severity: str = "P2",
        cluster_health: str = "HEALTHY",
        affected_replica_count: int = 2,
    ) -> RiskAssessment:
        """
        Calculates deterministic risk score and classification.
        """
        sev_norm = incident_severity.upper()
        svc_norm = action.target_service_name.lower()

        # 1. Base action risk weight
        base_scores = {
            RiskClassification.LOW: 0.15,
            RiskClassification.MODERATE: 0.40,
            RiskClassification.HIGH: 0.70,
            RiskClassification.CRITICAL: 0.90,
        }
        score = base_scores.get(action.risk_level, 0.30)

        # 2. Service Criticality factor
        if svc_norm in cls.CRITICAL_SERVICES:
            resource_criticality = "TIER_1_CORE"
            score += 0.20
        elif svc_norm in cls.MODERATE_SERVICES:
            resource_criticality = "TIER_2_INTERNAL"
            score += 0.10
        else:
            resource_criticality = "TIER_3_PERIPHERAL"

        # 3. Incident Severity adjustment
        if sev_norm in ("P1", "SEV-1", "CRITICAL"):
            # Critical incidents raise the stakes for destructive operations
            if action.action_type in ("rollback", "scale"):
                score += 0.10
        elif sev_norm in ("P4", "SEV-4", "LOW"):
            score -= 0.05

        # 4. Action Reversibility deduction or penalty
        if not action.is_reversible:
            score += 0.15
            data_integrity = "POTENTIAL_RISK"
        else:
            score -= 0.05
            data_integrity = "PRESERVED"

        # 5. Affected resource count / blast radius
        if affected_replica_count > 5:
            score += 0.15
        elif affected_replica_count > 2:
            score += 0.05

        # 6. Cluster Health factor
        if cluster_health != "HEALTHY":
            score += 0.20

        # Clamp score between 0.05 and 0.98
        final_score = round(max(0.05, min(0.98, score)), 2)

        # Deterministic classification boundaries
        if final_score >= 0.85:
            classification = RiskClassification.CRITICAL
            req_human = True
            req_emergency = True
        elif final_score >= 0.65:
            classification = RiskClassification.HIGH
            req_human = True
            req_emergency = False
        elif final_score >= 0.35:
            classification = RiskClassification.MODERATE
            req_human = True
            req_emergency = False
        else:
            classification = RiskClassification.LOW
            req_human = False
            req_emergency = False

        # Build explainable impact narrative and failure scenarios
        scenarios: List[str] = []
        safeguards: List[str] = [
            "Validate cluster identity & namespace before execution",
            "Capture pre-execution state snapshot",
            "Monitor telemetry recovery criteria post-execution",
        ]

        if action.action_type == "rollback":
            scenarios.append("Rollback to older revision may reintroduce previously resolved bugs.")
            safeguards.append("Verify destination image digest matches trusted build.")
        elif action.action_type == "restart":
            scenarios.append("Rolling restart may temporarily lower ingress request processing capacity.")
            safeguards.append("Enforce minimum 1 ready replica during rollout.")
        elif action.action_type == "scale":
            scenarios.append("Replica scale-down could elevate latency if traffic spikes.")
            safeguards.append("Enforce minimum replica floor of 1.")

        if not action.is_reversible:
            scenarios.append("Action has no automatic rollback procedure.")
            safeguards.append("Require senior SRE confirmation before applying.")

        explanation = (
            f"Risk classified as {classification.value} (score: {final_score:.2f}) on {resource_criticality} "
            f"service '{action.target_service_name}'. "
            f"Reversible: {action.is_reversible}. "
            f"Human approval required: {req_human}."
        )

        return RiskAssessment(
            plan_id=plan_id,
            action_id=action.action_id,
            target_resource=action.target_resource,
            risk_score=final_score,
            risk_classification=classification,
            incident_severity=incident_severity,
            resource_criticality=resource_criticality,
            affected_resource_count=affected_replica_count,
            availability_impact=f"Transient impact on {action.target_service_name}",
            data_integrity_risk=data_integrity,
            cluster_health_status=cluster_health,
            is_reversible=action.is_reversible,
            rollback_available=action.rollback_action_id is not None,
            potential_failure_scenarios=scenarios,
            required_safeguards=safeguards,
            impact_explanation=explanation,
            requires_human_approval=req_human,
            requires_emergency_override=req_emergency,
        )


risk_engine = IntelligentRiskEngine()
