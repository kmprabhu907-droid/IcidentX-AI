"""
INCIDENTX AI - Investigation Quality & Consensus Agent (Phase 10 Agent 11)
Reviews findings across all agents, cross-examines evidence validity, identifies contradictions,
flags unsupported conclusions, evaluates confidence, and prevents forced false consensus.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.collaboration_protocol import (
    CollaborationMessageType,
    collaboration_protocol_engine,
)
from backend.app.services.investigation.evidence_engine import (
    EvidenceCategory,
    EvidenceVerificationStatus,
    shared_evidence_engine,
)


class InvestigationQualityConsensusAgent(BaseInvestigationAgent):
    """
    Specialized agent conducting quality control, contradiction cross-examination,
    and consensus validation over multi-agent findings.
    """

    def __init__(self):
        super().__init__(
            name="InvestigationQualityConsensusAgent",
            role="consensus_quality",
            execution_phase="QUALITY_AND_CONSENSUS",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Conducting consensus and contradiction audit for incident {incident_id}")

        env_mode = environment_manager.active_mode.value
        affected_service = state.get("affected_service", "cluster")
        investigation_id = state.get("investigation_id", "inv-default")

        # 1. Fetch all accumulated evidence
        evidence_items = await shared_evidence_engine.list_evidence(incident_id, session)

        facts = [e for e in evidence_items if e.is_fact]
        interpretations = [e for e in evidence_items if not e.is_fact]
        contradictions = [e for e in evidence_items if e.is_contradictory or e.verification_status == "CONTRADICTED"]

        # 2. Quality review rules
        quality_score = 1.0
        audit_notes: List[str] = []

        if len(facts) < 2:
            quality_score -= 0.3
            audit_notes.append("Sparse empirical evidence base (<2 facts observed).")

        if contradictions:
            quality_score -= 0.2 * len(contradictions)
            audit_notes.append(f"Detected {len(contradictions)} contradictory evidence observation(s).")

            # Publish contradiction alert on collaboration protocol
            await collaboration_protocol_engine.send_message(
                incident_id=incident_id,
                investigation_id=investigation_id,
                sender_agent=self.name,
                message_type=CollaborationMessageType.REPORT_CONTRADICTION,
                summary=f"Consensus Agent flagged {len(contradictions)} contradictory exhibits in investigation.",
                payload={"contradictions": [c.description for c in contradictions]},
                session=session,
            )

        quality_score = max(0.1, min(1.0, quality_score))

        # 3. Consensus determination
        is_consensus_reached = len(contradictions) == 0 and len(facts) >= 2
        consensus_status = "CONSENSUS_REACHED" if is_consensus_reached else "INCONCLUSIVE_DISAGREEMENT" if contradictions else "PENDING_ADDITIONAL_EVIDENCE"

        consensus_summary = {
            "quality_score": round(quality_score, 2),
            "consensus_status": consensus_status,
            "total_facts": len(facts),
            "total_interpretations": len(interpretations),
            "total_contradictions": len(contradictions),
            "audit_notes": audit_notes,
        }

        state["consensus_review"] = consensus_summary
        state["consensus_status"] = consensus_status
        state["consensus_quality_score"] = round(quality_score, 2)

        # Record consensus review finding in shared evidence engine
        await shared_evidence_engine.record_evidence(
            incident_id=incident_id,
            source_agent=self.name,
            evidence_category=EvidenceCategory.AI_HYPOTHESIS,
            observation=(
                f"Consensus Audit [{consensus_status}]: Quality score {round(quality_score, 2)}. "
                f"Evaluated {len(facts)} empirical facts and {len(interpretations)} interpretations. "
                f"Contradictions detected: {len(contradictions)}."
            ),
            investigation_id=investigation_id,
            resource_reference=affected_service,
            confidence_score=quality_score,
            environment=env_mode,
            verification_status=EvidenceVerificationStatus.VERIFIED if is_consensus_reached else EvidenceVerificationStatus.INSUFFICIENT,
            is_fact=False,
            session=session,
        )

        logger.info(
            f"[{self.name}] Audit finished for {incident_id}: status={consensus_status}, quality={quality_score}"
        )
        return state


investigation_quality_consensus_agent = InvestigationQualityConsensusAgent()
