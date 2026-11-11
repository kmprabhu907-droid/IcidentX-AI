"""
INCIDENTX AI - Core Reliability Memory Engine
Integrates historical incident storage, multi-feature fingerprint matching,
similarity ranking, remediation learning, and explainable memory retrieval.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.reliability import IncidentMemory, RegressionRecord
from backend.app.models.remediation import RemediationAction
from backend.app.models.telemetry import TelemetryEvent
from backend.app.services.observability.regression.fingerprint import (
    FingerprintBuilder,
    IncidentFingerprint,
    extract_root_cause_categories,
    normalize_error_string,
)
from backend.app.services.observability.regression.similarity import (
    IncidentSimilarityEngine,
    SimilarityResult,
)
from backend.app.services.reliability_memory.models import (
    HistoricalMemoryEntry,
    MemorySearchExplanation,
)
from backend.app.services.reliability_memory.remediation_learner import (
    RemediationLearner,
    SIDE_EFFECT_REGISTRY,
)


class ReliabilityMemoryEngine:
    """
    Central persistent intelligence engine for Stage 5.4.
    Learns from past incidents, investigations, safe remediations, and regressions.
    """

    @classmethod
    async def build_memory_entry(
        cls,
        incident_id: str,
        db: AsyncSession,
    ) -> Optional[HistoricalMemoryEntry]:
        """
        Gathers and aggregates the full 20-dimension historical memory entry for an incident.
        """
        # 1. Fetch Incident
        inc_q = select(Incident).where(Incident.id == incident_id)
        inc_r = await db.execute(inc_q)
        incident = inc_r.scalar_one_or_none()
        if not incident:
            return None

        # 2. Fetch Evidence
        ev_q = select(Evidence).where(Evidence.incident_id == incident_id)
        ev_r = await db.execute(ev_q)
        evidence_rows = ev_r.scalars().all()

        supporting: List[Dict[str, Any]] = []
        contradicting: List[Dict[str, Any]] = []
        error_signatures: List[str] = []
        telemetry_patterns: Dict[str, float] = {}

        for ev in evidence_rows:
            ev_dict = {
                "id": ev.id,
                "evidence_type": ev.evidence_type,
                "source_system": ev.source_system,
                "description": ev.description,
                "confidence_score": ev.confidence_score,
                "verification_status": ev.verification_status,
            }
            if ev.is_contradictory:
                contradicting.append(ev_dict)
            else:
                supporting.append(ev_dict)

            if ev.evidence_type == "error_log":
                norm_err = normalize_error_string(ev.description)
                if norm_err and norm_err not in error_signatures:
                    error_signatures.append(norm_err)
            elif ev.evidence_type == "metric_anomaly":
                # Parse numeric anomaly if possible
                telemetry_patterns[ev.source_system] = ev.confidence_score * 100.0

        # 3. Fetch Root Cause Hypotheses
        hyp_q = select(RootCauseHypothesis).where(RootCauseHypothesis.incident_id == incident_id)
        hyp_r = await db.execute(hyp_q)
        hypotheses_rows = hyp_r.scalars().all()

        hypotheses: List[Dict[str, Any]] = []
        confirmed_rc: Optional[str] = None
        for h in hypotheses_rows:
            hypotheses.append({
                "id": h.id,
                "hypothesis_text": h.hypothesis_text,
                "probability_score": h.probability_score,
                "status": h.status,
                "is_confirmed": h.is_confirmed_root_cause,
            })
            if h.is_confirmed_root_cause or h.status == "ACCEPTED":
                confirmed_rc = h.hypothesis_text

        # 4. Fetch Remediation Actions
        rem_q = select(RemediationAction).where(RemediationAction.incident_id == incident_id)
        rem_r = await db.execute(rem_q)
        rem_rows = rem_r.scalars().all()

        remediations: List[Dict[str, Any]] = []
        overall_outcome = "UNKNOWN"
        side_effects: List[str] = []

        for r in rem_rows:
            remediations.append({
                "id": r.id,
                "action_id": r.action_id,
                "name": r.name,
                "target_service_name": r.target_service_name,
                "status": r.status,
                "verification_status": r.verification_status,
                "rollback_status": r.rollback_status,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            })
            if r.action_id in SIDE_EFFECT_REGISTRY:
                side_effects.extend(SIDE_EFFECT_REGISTRY[r.action_id])

            if r.status == "FAILED" or r.verification_status == "FAILED" or r.rollback_status in ["ROLLED_BACK", "ROLLBACK_FAILED"]:
                overall_outcome = "FAILED"
            elif r.verification_status == "VERIFIED" and overall_outcome != "FAILED":
                overall_outcome = "SUSTAINED_SUCCESS"

        # 5. Fetch Regressions
        regr_q = select(RegressionRecord).where(RegressionRecord.incident_id == incident_id)
        regr_r = await db.execute(regr_q)
        regressions = regr_r.scalars().all()
        if regressions and overall_outcome == "SUSTAINED_SUCCESS":
            overall_outcome = "TEMPORARY_SUCCESS"

        # 6. Extract root cause category & affected services
        all_text = [incident.title, incident.summary or ""] + [h["hypothesis_text"] for h in hypotheses]
        rc_categories = extract_root_cause_categories(all_text)
        primary_rc = list(rc_categories)[0] if rc_categories else "UNKNOWN"

        aff_services: List[str] = []
        if incident.impact_scope:
            aff_services = [s.strip() for s in incident.impact_scope.split(",") if s.strip()]
        if not aff_services:
            aff_services = ["unknown-service"]

        primary_service = aff_services[0] if aff_services else "unknown-service"

        # 7. Formulate learned lessons
        learned_lessons: List[str] = []
        if confirmed_rc:
            learned_lessons.append(f"Confirmed root cause was verified: '{confirmed_rc}'.")
        if overall_outcome == "SUSTAINED_SUCCESS":
            learned_lessons.append("Remediation strategy achieved sustained recovery without recurrence.")
        elif overall_outcome == "TEMPORARY_SUCCESS":
            learned_lessons.append("Remediation yielded only temporary stability before metric regression occurred.")
        elif overall_outcome == "FAILED":
            learned_lessons.append("Initial intervention failed verification or required emergency rollback.")

        return HistoricalMemoryEntry(
            incident_id=incident.id,
            title=incident.title,
            summary=incident.summary or "",
            severity=incident.severity,
            status=incident.status,
            detected_at=incident.detected_at.isoformat() if incident.detected_at else None,
            resolved_at=incident.resolved_at.isoformat() if incident.resolved_at else None,
            mttr_seconds=incident.mttr_seconds,
            primary_service=primary_service,
            affected_services=aff_services,
            root_cause_category=primary_rc,
            confirmed_root_cause=confirmed_rc,
            hypotheses=hypotheses,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            telemetry_patterns=telemetry_patterns,
            error_signatures=error_signatures,
            dependency_relationships={
                "api-gateway": ["order-service", "auth-service", "inventory-service"],
                "order-service": ["payment-service", "inventory-service", "postgres-db"],
                "payment-service": ["postgres-db"],
                "inventory-service": ["postgres-db", "redis-cache"],
                "auth-service": ["redis-cache", "postgres-db"],
            },
            remediation_actions=remediations,
            remediation_outcome=overall_outcome,
            learned_lessons=learned_lessons,
            side_effects=list(set(side_effects)),
            regressions_count=len(regressions),
        )

    @classmethod
    async def index_incident_memory(
        cls,
        incident_id: str,
        db: AsyncSession,
    ) -> Optional[IncidentMemory]:
        """
        Indexes or updates an incident's pre-computed memory record in `incident_memories`.
        """
        entry = await cls.build_memory_entry(incident_id, db)
        if not entry:
            return None

        # Check existing memory record
        q = select(IncidentMemory).where(IncidentMemory.incident_id == incident_id)
        r = await db.execute(q)
        existing = r.scalar_one_or_none()

        search_corpus = f"{entry.title} {entry.summary} {entry.primary_service} {' '.join(entry.affected_services)} {entry.root_cause_category} {' '.join(entry.error_signatures)}"

        if existing:
            existing.primary_service = entry.primary_service
            existing.affected_services = json.dumps(entry.affected_services)
            existing.severity = entry.severity
            existing.fingerprint_vector = json.dumps(entry.telemetry_patterns)
            existing.error_signatures = json.dumps(entry.error_signatures)
            existing.root_cause_category = entry.root_cause_category
            existing.confirmed_root_cause = entry.confirmed_root_cause
            existing.remediation_outcome = entry.remediation_outcome
            existing.remediation_side_effects = json.dumps(entry.side_effects)
            existing.learned_lessons = json.dumps(entry.learned_lessons)
            existing.search_vector = search_corpus
            await db.commit()
            return existing

        new_mem = IncidentMemory(
            incident_id=entry.incident_id,
            primary_service=entry.primary_service,
            affected_services=json.dumps(entry.affected_services),
            severity=entry.severity,
            fingerprint_vector=json.dumps(entry.telemetry_patterns),
            error_signatures=json.dumps(entry.error_signatures),
            root_cause_category=entry.root_cause_category,
            confirmed_root_cause=entry.confirmed_root_cause,
            remediation_action_ids=json.dumps([r["id"] for r in entry.remediation_actions]),
            remediation_outcome=entry.remediation_outcome,
            remediation_side_effects=json.dumps(entry.side_effects),
            learned_lessons=json.dumps(entry.learned_lessons),
            search_vector=search_corpus,
        )
        db.add(new_mem)
        await db.commit()
        return new_mem

    @classmethod
    async def search_memory(
        cls,
        db: AsyncSession,
        query_text: Optional[str] = None,
        service_name: Optional[str] = None,
        severity: Optional[str] = None,
        root_cause_category: Optional[str] = None,
        limit: int = 20,
    ) -> List[HistoricalMemoryEntry]:
        """
        Structured multi-criteria SQL query across indexed incident memory.
        """
        stmt = select(Incident).order_by(desc(Incident.detected_at))

        if severity:
            stmt = stmt.where(Incident.severity == severity)

        result = await db.execute(stmt)
        incidents = result.scalars().all()

        matching_entries: List[HistoricalMemoryEntry] = []
        for inc in incidents:
            # Check service name match
            if service_name and inc.impact_scope and service_name not in inc.impact_scope:
                continue

            entry = await cls.build_memory_entry(inc.id, db)
            if not entry:
                continue

            # Check root cause category filter
            if root_cause_category and entry.root_cause_category != root_cause_category:
                continue

            # Check text search filter
            if query_text:
                q_lower = query_text.lower()
                corpus = f"{entry.title} {entry.summary} {entry.root_cause_category} {' '.join(entry.error_signatures)}".lower()
                if q_lower not in corpus:
                    continue

            matching_entries.append(entry)
            if len(matching_entries) >= limit:
                break

        return matching_entries

    @classmethod
    async def find_similar_incidents(
        cls,
        target_fingerprint: IncidentFingerprint,
        db: AsyncSession,
        min_similarity: float = 0.30,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves historical incidents ranked by multi-dimensional fingerprint similarity,
        complete with the 6 standard memory explanation answers.
        """
        # Fetch candidate historical incidents
        stmt = select(Incident).order_by(desc(Incident.detected_at)).limit(30)
        res = await db.execute(stmt)
        historical_incidents = res.scalars().all()

        matches: List[Tuple[HistoricalMemoryEntry, SimilarityResult, MemorySearchExplanation]] = []

        for inc in historical_incidents:
            if inc.id == target_fingerprint.incident_id:
                continue

            entry = await cls.build_memory_entry(inc.id, db)
            if not entry:
                continue

            # Build historical fingerprint
            hist_fp = FingerprintBuilder.build(
                incident_id=entry.incident_id,
                primary_service=entry.primary_service,
                affected_services=entry.affected_services,
                telemetry_anomalies=entry.telemetry_patterns,
                error_logs=entry.error_signatures,
                hypotheses=[entry.summary] + [h["hypothesis_text"] for h in entry.hypotheses],
                severity=entry.severity,
            )

            # Compute similarity
            sim_res = IncidentSimilarityEngine.compare_fingerprints(target_fingerprint, hist_fp)

            if sim_res.overall_similarity_score >= min_similarity:
                # Generate explainable response
                explanation = cls.explain_memory_match(target_fingerprint, entry, sim_res)
                matches.append((entry, sim_res, explanation))

        # Sort descending by similarity score
        matches.sort(key=lambda m: m[1].overall_similarity_score, reverse=True)

        results: List[Dict[str, Any]] = []
        for entry, sim_res, expl in matches[:limit]:
            results.append({
                "incident": entry.to_dict(),
                "similarity": sim_res.to_dict(),
                "explanation": expl.to_dict(),
            })

        return results

    @classmethod
    def explain_memory_match(
        cls,
        target_fp: IncidentFingerprint,
        hist_entry: HistoricalMemoryEntry,
        sim_res: SimilarityResult,
    ) -> MemorySearchExplanation:
        """
        Formulates the 6 standard explainable answers for historical memory retrieval:
          1. Why was it selected?
          2. How similar is it?
          3. Which evidence matches?
          4. Which evidence differs?
          5. Whether the previous remediation worked.
          6. What lessons can be reused.
        """
        # 1. Why selected
        reasons: List[str] = []
        if sim_res.services_similarity >= 0.7:
            reasons.append(f"Affected services overlap ({', '.join(sim_res.shared_services)})")
        if sim_res.root_cause_similarity >= 0.6:
            reasons.append(f"Matching root-cause taxonomy ({', '.join(sim_res.shared_root_causes)})")
        if sim_res.metric_vector_similarity >= 0.7:
            reasons.append("Concordant metric anomaly departures")
        why_selected = "; ".join(reasons) if reasons else f"Shared architectural boundaries with {hist_entry.primary_service}."

        # 3. Evidence matches
        ev_matches: List[str] = []
        if sim_res.shared_services:
            ev_matches.append(f"Common services: {', '.join(sim_res.shared_services)}")
        if sim_res.shared_metrics:
            ev_matches.append(f"Common anomalous metrics: {', '.join(sim_res.shared_metrics)}")
        if sim_res.shared_root_causes:
            ev_matches.append(f"Common root causes: {', '.join(sim_res.shared_root_causes)}")
        if sim_res.shared_error_signatures:
            ev_matches.append(f"Shared error patterns: {len(sim_res.shared_error_signatures)} canonical logs")

        # 4. Evidence differs
        ev_differs: List[str] = []
        diff_services = target_fp.affected_services.symmetric_difference(set(hist_entry.affected_services))
        if diff_services:
            ev_differs.append(f"Discrepant blast radius: {', '.join(list(diff_services)[:3])}")
        diff_causes = target_fp.root_cause_categories.symmetric_difference(set([hist_entry.root_cause_category]))
        if diff_causes:
            ev_differs.append(f"Divergent classification: {', '.join(list(diff_causes)[:2])}")

        # 5. Did previous remediation work?
        outcome = hist_entry.remediation_outcome
        if outcome == "SUSTAINED_SUCCESS":
            rem_work = "Yes, previous remediation achieved sustained recovery without recurring regressions."
        elif outcome == "TEMPORARY_SUCCESS":
            rem_work = "Partially, provided temporary stabilization before regression occurred."
        elif outcome == "FAILED":
            rem_work = "No, previous remediation action failed verification or triggered a rollback."
        else:
            rem_work = f"Inconclusive / status was {outcome}."

        # 6. Reusable lessons
        lessons: List[str] = []
        if hist_entry.confirmed_root_cause:
            lessons.append(f"Consider investigating '{hist_entry.confirmed_root_cause}' first.")
        if hist_entry.side_effects:
            lessons.append(f"Beware known side-effects: {'; '.join(hist_entry.side_effects)}.")
        if not lessons:
            lessons.append("Perform empirical metric verification before declaring complete recovery.")

        return MemorySearchExplanation(
            why_selected=why_selected,
            similarity_score=sim_res.overall_similarity_score,
            evidence_matches=ev_matches or ["Topological vicinity"],
            evidence_differs=ev_differs or ["None identified"],
            previous_remediation_effective=rem_work,
            reusable_lessons=lessons,
        )
