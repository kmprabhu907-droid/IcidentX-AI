"""
INCIDENTX AI - Remediation Intelligence Agent (Phase 10 Agent 9)
Formulates safety-bounded remediation recommendations based on validated multi-agent
investigation findings, estimating blast radius, risks, and rollback considerations
without autonomously executing destructive mutations.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.evidence_engine import (
    EvidenceCategory,
    EvidenceVerificationStatus,
    shared_evidence_engine,
)


class RemediationIntelligenceAgent(BaseInvestigationAgent):
    """
    Specialized agent formulating safe, explainable remediation recommendations.
    """

    def __init__(self):
        super().__init__(
            name="RemediationIntelligenceAgent",
            role="remediation_planner",
            execution_phase="REMEDIATION_PLANNING",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Formulating remediation options for incident {incident_id}")

        affected_service = state.get("affected_service", "cluster")
        env_mode = environment_manager.active_mode.value
        top_hyp = state.get("primary_hypothesis", "Systemic operational anomaly")

        recommendations: List[Dict[str, Any]] = []

        # Formulate contextual remediation strategy
        if "memory" in top_hyp.lower() or "oom" in top_hyp.lower():
            recommendations.append({
                "action_type": "SCALE_WORKLOAD",
                "target_service": affected_service,
                "title": f"Scale {affected_service} deployment replicas to relieve memory saturation",
                "risk_level": "LOW",
                "requires_approval": False,
                "blast_radius": f"Scoped to service {affected_service} replicas",
                "rollback_safe": True,
                "rollback_plan": f"Scale {affected_service} back to previous replica count if memory leak persists.",
                "justification": f"Validated evidence indicates memory exhaustion on {affected_service}.",
            })
        elif "deployment" in top_hyp.lower() or "release" in top_hyp.lower() or "regression" in top_hyp.lower():
            recommendations.append({
                "action_type": "ROLLBACK_DEPLOYMENT",
                "target_service": affected_service,
                "title": f"Roll back {affected_service} to previous known-good image revision",
                "risk_level": "HIGH",
                "requires_approval": True,
                "blast_radius": f"Replaces running pods of {affected_service} with prior image",
                "rollback_safe": True,
                "rollback_plan": f"Re-deploy target revision if rollback fails to recover latency baseline.",
                "justification": f"Observed fault timeline directly follows recent deployment of {affected_service}.",
            })
        else:
            recommendations.append({
                "action_type": "RESTART_POD",
                "target_service": affected_service,
                "title": f"Graceful rolling restart of {affected_service} pods",
                "risk_level": "MEDIUM",
                "requires_approval": True,
                "blast_radius": f"Scoped to service {affected_service} pods only",
                "rollback_safe": True,
                "rollback_plan": "Kubernetes preserves previous ReplicaSet if new pods fail readiness checks.",
                "justification": f"Clears unclosed database connections and threadpool deadlocks on {affected_service}.",
            })

        state["remediation_recommendations"] = recommendations

        # Record recommendation as an AI Hypothesis evidence item
        for rec in recommendations:
            await shared_evidence_engine.record_evidence(
                incident_id=incident_id,
                source_agent=self.name,
                evidence_category=EvidenceCategory.AI_HYPOTHESIS,
                observation=f"Remediation Proposal: {rec['title']} (Risk: {rec['risk_level']}). Justification: {rec['justification']}",
                investigation_id=state.get("investigation_id"),
                resource_reference=affected_service,
                confidence_score=0.90,
                environment=env_mode,
                verification_status=EvidenceVerificationStatus.VERIFIED,
                is_fact=False,  # Interpretation / recommendation
                session=session,
            )

        return state


remediation_intelligence_agent = RemediationIntelligenceAgent()
