"""
INCIDENTX AI - AI Reasoning Memory Bridge (Phase 8.4)
Bridges AI Courtroom Reasoning reports with the ReliabilityMemoryEngine.
Tracks hypothesis lifecycle states (PROPOSED, INVESTIGATED, VERIFIED, REJECTED, SUPERSEDED),
persists structured lessons learned, and enables cross-incident knowledge retrieval.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.investigation import RootCauseHypothesis, Evidence
from backend.app.models.reliability import IncidentMemory
from backend.app.models.incident import Incident
from backend.app.services.ai.models import (
    AIIncidentReasoningReport,
    CourtroomHypothesis,
    CourtroomVerdict,
)
from backend.app.services.reliability_memory.engine import ReliabilityMemoryEngine


class HypothesisLifecycleState:
    PROPOSED = "PROPOSED"
    INVESTIGATED = "INVESTIGATED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ReasoningMemoryBridge:
    """
    Synchronizes AI reasoning outputs, courtroom verdicts, and evidence-grounded
    conclusions into the core ReliabilityMemoryEngine and investigation database models.
    """

    def __init__(self):
        self._in_memory_records: Dict[str, Dict[str, Any]] = {}

    async def record_reasoning_outcome(
        self,
        report: AIIncidentReasoningReport,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Takes an AIIncidentReasoningReport, records lifecycle states, and bridges to memory engine.
        """
        return await self.record_reasoning_verdict(
            incident_id=report.incident_id,
            report=report,
            db=session,
        )

    async def record_reasoning_verdict(
        self,
        incident_id: str,
        report: AIIncidentReasoningReport,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Takes an AIIncidentReasoningReport, extracts CourtroomVerdict and hypotheses,
        transitions their lifecycle states, updates the database, and indexes
        into the ReliabilityMemoryEngine.
        """
        verdict = report.courtroom_verdict
        leading_hyp_id = verdict.leading_hypothesis_id
        timestamp = datetime.now(timezone.utc).isoformat()

        lifecycle_records = []
        leading_hyp: Optional[CourtroomHypothesis] = None

        # Process each hypothesis
        for hyp in verdict.competing_hypotheses:
            is_leading = (hyp.hypothesis_id == leading_hyp_id or hyp.is_leading)
            if is_leading:
                leading_hyp = hyp

            # Determine lifecycle status
            if is_leading:
                if verdict.confidence_score >= 0.70 and len(hyp.supporting_evidence_ids) > 0:
                    status = HypothesisLifecycleState.VERIFIED
                else:
                    status = HypothesisLifecycleState.INVESTIGATED
            elif hyp.confidence_score <= 0.35 or len(hyp.contradicting_evidence_ids) > 0:
                status = HypothesisLifecycleState.REJECTED
            else:
                status = HypothesisLifecycleState.INVESTIGATED

            record = {
                "hypothesis_id": hyp.hypothesis_id,
                "title": hyp.title,
                "culprit_service": hyp.culprit_service,
                "explanation": hyp.explanation,
                "confidence_score": hyp.confidence_score,
                "status": status,
                "is_leading": is_leading,
                "supporting_evidence_ids": hyp.supporting_evidence_ids,
                "contradicting_evidence_ids": hyp.contradicting_evidence_ids,
                "recorded_at": timestamp,
            }
            lifecycle_records.append(record)

        summary_data = {
            "incident_id": incident_id,
            "verdict_summary": verdict.verdict_summary,
            "confidence_score": verdict.confidence_score,
            "leading_hypothesis": leading_hyp.model_dump() if leading_hyp else None,
            "hypotheses_lifecycle": lifecycle_records,
            "evidence_count": len(report.evidence_items),
            "model_attribution": report.model_attribution.model_dump(),
            "recorded_at": timestamp,
            "lessons_learned": [
                f"Root cause investigation executed via {report.model_attribution.provider_name} ({report.model_attribution.model_name}).",
                f"Identified leading hypothesis: '{leading_hyp.title if leading_hyp else 'Inconclusive'}'.",
                f"Courtroom confidence score: {verdict.confidence_score:.2f}.",
            ],
        }

        # Store in in-memory registry
        self._in_memory_records[incident_id] = summary_data

        # If DB session provided, persist to database models
        if db is not None:
            try:
                # 1. Update or create RootCauseHypothesis rows in DB
                for h_rec in lifecycle_records:
                    hyp_q = select(RootCauseHypothesis).where(
                        RootCauseHypothesis.incident_id == incident_id,
                        RootCauseHypothesis.hypothesis_text == h_rec["explanation"],
                    )
                    r = await db.execute(hyp_q)
                    db_hyp = r.scalar_one_or_none()

                    if db_hyp:
                        db_hyp.status = h_rec["status"]
                        db_hyp.probability_score = h_rec["confidence_score"]
                        db_hyp.is_confirmed_root_cause = (h_rec["status"] == HypothesisLifecycleState.VERIFIED)
                        db_hyp.judicial_ruling = verdict.verdict_summary
                    else:
                        new_hyp = RootCauseHypothesis(
                            incident_id=incident_id,
                            hypothesis_text=h_rec["explanation"],
                            probability_score=h_rec["confidence_score"],
                            status=h_rec["status"],
                            is_confirmed_root_cause=(h_rec["status"] == HypothesisLifecycleState.VERIFIED),
                            judicial_ruling=verdict.verdict_summary,
                            evidence_count=len(h_rec["supporting_evidence_ids"]),
                            contradiction_count=len(h_rec["contradicting_evidence_ids"]),
                        )
                        db.add(new_hyp)

                # 2. Update Incident summary if verified
                if leading_hyp and verdict.confidence_score >= 0.70:
                    inc_q = select(Incident).where(Incident.id == incident_id)
                    inc_r = await db.execute(inc_q)
                    incident = inc_r.scalar_one_or_none()
                    if incident:
                        incident.summary = f"Root cause verified: {leading_hyp.title} (Confidence: {verdict.confidence_score:.2f})"

                await db.commit()
            except Exception as e:
                logger.warning(f"[ReasoningMemoryBridge] DB sync failed (non-fatal): {e}")
                await db.rollback()

        return summary_data

    async def get_reasoning_lifecycle(
        self,
        incident_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves the lifecycle state and investigation trail for an incident's hypotheses.
        """
        # First check in-memory
        if incident_id in self._in_memory_records:
            return self._in_memory_records[incident_id]

        # Otherwise query DB if available
        if db is not None:
            try:
                hyp_q = select(RootCauseHypothesis).where(RootCauseHypothesis.incident_id == incident_id)
                hyp_r = await db.execute(hyp_q)
                hypotheses = hyp_r.scalars().all()

                if hypotheses:
                    records = [
                        {
                            "hypothesis_id": h.id,
                            "title": h.hypothesis_text[:40],
                            "explanation": h.hypothesis_text,
                            "confidence_score": h.probability_score,
                            "status": h.status,
                            "is_leading": h.is_confirmed_root_cause,
                            "judicial_ruling": h.judicial_ruling,
                            "evidence_count": h.evidence_count,
                            "contradiction_count": h.contradiction_count,
                        }
                        for h in hypotheses
                    ]
                    return {
                        "incident_id": incident_id,
                        "hypotheses_lifecycle": records,
                        "status": "LOADED_FROM_DB",
                    }
            except Exception as e:
                logger.warning(f"[ReasoningMemoryBridge] DB read failed: {e}")

        return {
            "incident_id": incident_id,
            "hypotheses_lifecycle": [],
            "status": "NOT_FOUND",
        }

    async def update_hypothesis_lifecycle(
        self,
        incident_id: str,
        hypothesis_id: str,
        new_status: str,
        reason: str = "",
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Explicitly transitions a hypothesis between lifecycle states:
        PROPOSED, INVESTIGATED, VERIFIED, REJECTED, SUPERSEDED.
        """
        valid_states = {
            HypothesisLifecycleState.PROPOSED,
            HypothesisLifecycleState.INVESTIGATED,
            HypothesisLifecycleState.VERIFIED,
            HypothesisLifecycleState.REJECTED,
            HypothesisLifecycleState.SUPERSEDED,
        }
        if new_status not in valid_states:
            raise ValueError(f"Invalid lifecycle state: {new_status}. Allowed: {valid_states}")

        # Update in-memory record if exists
        updated_in_mem = False
        if incident_id in self._in_memory_records:
            for hyp in self._in_memory_records[incident_id].get("hypotheses_lifecycle", []):
                if hyp.get("hypothesis_id") == hypothesis_id:
                    hyp["status"] = new_status
                    hyp["status_reason"] = reason
                    hyp["updated_at"] = datetime.now(timezone.utc).isoformat()
                    updated_in_mem = True
                    break

        # Update DB if session provided
        if db is not None:
            try:
                hyp_q = select(RootCauseHypothesis).where(
                    RootCauseHypothesis.incident_id == incident_id,
                    RootCauseHypothesis.id == hypothesis_id,
                )
                r = await db.execute(hyp_q)
                db_hyp = r.scalar_one_or_none()
                if db_hyp:
                    db_hyp.status = new_status
                    if reason:
                        db_hyp.judicial_ruling = f"Lifecycle updated to {new_status}: {reason}"
                    if new_status == HypothesisLifecycleState.VERIFIED:
                        db_hyp.is_confirmed_root_cause = True
                    elif new_status in {HypothesisLifecycleState.REJECTED, HypothesisLifecycleState.SUPERSEDED}:
                        db_hyp.is_confirmed_root_cause = False
                    await db.commit()
                    return True
            except Exception as e:
                logger.warning(f"[ReasoningMemoryBridge] Failed to update hypothesis lifecycle in DB: {e}")
                await db.rollback()

        return updated_in_mem

    async def query_similar_reasoning_cases(
        self,
        service_name: str,
        symptoms: str,
        db: Optional[AsyncSession] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches historical memories for incidents that match the service name
        and symptom query, returning verified root causes and remediation outcomes.
        """
        if db is not None:
            try:
                results, _ = await ReliabilityMemoryEngine.search_memory(
                    query_text=f"{service_name} {symptoms}",
                    db=db,
                    max_results=limit,
                )
                cases = []
                for entry in results:
                    cases.append({
                        "incident_id": entry.incident_id,
                        "title": entry.title,
                        "primary_service": entry.primary_service,
                        "root_cause_category": entry.root_cause_category,
                        "confirmed_root_cause": entry.confirmed_root_cause,
                        "remediation_outcome": entry.remediation_outcome,
                        "learned_lessons": entry.learned_lessons,
                    })
                return cases
            except Exception as e:
                logger.warning(f"[ReasoningMemoryBridge] search_memory query failed: {e}")

        # In-memory fallback
        matches = []
        for inc_id, rec in self._in_memory_records.items():
            leading = rec.get("leading_hypothesis") or {}
            text = f"{leading.get('title', '')} {leading.get('explanation', '')} {leading.get('culprit_service', '')}".lower()
            if service_name.lower() in text or any(word in text for word in symptoms.lower().split()):
                matches.append({
                    "incident_id": inc_id,
                    "title": f"Incident {inc_id}",
                    "primary_service": service_name,
                    "root_cause_category": "AI_INVESTIGATED",
                    "confirmed_root_cause": leading.get("title"),
                    "remediation_outcome": "INVESTIGATED",
                    "learned_lessons": rec.get("lessons_learned", []),
                })
                if len(matches) >= limit:
                    break
        return matches


# Global singleton instance
reasoning_memory_bridge = ReasoningMemoryBridge()
