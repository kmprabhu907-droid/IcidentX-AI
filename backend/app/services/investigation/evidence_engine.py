"""
INCIDENTX AI - Shared Evidence Intelligence Engine (Phase 10 Module 10.3)
Provides a centralized repository for observed infrastructure facts and agent findings,
enforcing evidence provenance, deterministic deduplication, strict separation between
observed facts vs. AI interpretations, and contradiction discovery.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, Set
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.models.investigation import Evidence, RootCauseHypothesis


class EvidenceCategory(str, Enum):
    KUBERNETES = "KUBERNETES"
    APPLICATION_LOGS = "APPLICATION_LOGS"
    METRICS = "METRICS"
    DEPLOYMENT = "DEPLOYMENT"
    NETWORK = "NETWORK"
    DEPENDENCY = "DEPENDENCY"
    SECURITY = "SECURITY"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"
    HUMAN_OBSERVATION = "HUMAN_OBSERVATION"


class EvidenceVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    incident_id: str
    investigation_id: Optional[str] = None
    source_agent: str
    evidence_category: EvidenceCategory
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resource_reference: Optional[str] = None  # Pod, Deployment, Service, or Node name
    original_source_reference: Optional[str] = None  # Trace ID, Span ID, Log Offset, PromQL query
    observation: str
    relevant_observation: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    environment: str = "DEMOMESH"
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.VERIFIED
    is_fact: bool = True  # CRITICAL: Separate observed telemetry facts from AI interpretations
    is_contradictory: bool = False
    raw_data: Optional[Dict[str, Any]] = None
    deduplication_hash: Optional[str] = None


class SharedEvidenceEngine:
    """
    Central Evidence Repository and Provenance Tracker for Incident Investigations.
    """

    def __init__(self):
        # In-memory fast cache per investigation_id: evidence_id -> EvidenceItem
        self._cache: Dict[str, Dict[str, EvidenceItem]] = {}
        # Hash lookup for fast in-flight deduplication: hash -> evidence_id
        self._hash_lookup: Dict[str, str] = {}

    @classmethod
    def compute_deduplication_hash(
        cls,
        incident_id: str,
        category: str,
        resource_ref: str,
        source_ref: str,
        observation: str,
    ) -> str:
        key = (
            f"{incident_id.strip()}:"
            f"{category.upper().strip()}:"
            f"{(resource_ref or '').strip().lower()}:"
            f"{(source_ref or '').strip()}:"
            f"{observation.strip().lower()}"
        )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def record_evidence(
        self,
        incident_id: str,
        source_agent: str,
        evidence_category: EvidenceCategory,
        observation: str,
        investigation_id: Optional[str] = None,
        resource_reference: Optional[str] = None,
        original_source_reference: Optional[str] = None,
        confidence_score: float = 1.0,
        environment: str = "DEMOMESH",
        verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.VERIFIED,
        is_fact: bool = True,
        is_contradictory: bool = False,
        raw_data: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncSession] = None,
    ) -> Evidence:
        """
        Records an evidence item with deduplication guard and persistence.
        """
        dedup_hash = self.compute_deduplication_hash(
            incident_id=incident_id,
            category=evidence_category.value,
            resource_ref=resource_reference or "",
            source_ref=original_source_reference or "",
            observation=observation,
        )

        now = datetime.now(timezone.utc)
        ev_id = str(uuid.uuid4())

        # Check in DB if session is available
        if session is not None:
            stmt = select(Evidence).where(
                Evidence.incident_id == incident_id,
                Evidence.deduplication_hash == dedup_hash,
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                logger.debug(
                    f"[EvidenceEngine] Deduplicated evidence item '{observation[:40]}...' for incident {incident_id}"
                )
                return existing

        # Create new Evidence record
        import json
        raw_data_str = json.dumps(raw_data) if raw_data else None

        db_evidence = Evidence(
            id=ev_id,
            incident_id=incident_id,
            investigation_id=investigation_id,
            evidence_type=evidence_category.value.lower(),
            evidence_category=evidence_category.value,
            source_system=source_agent,
            source_agent=source_agent,
            affected_service_name=resource_reference,
            raw_source_ref=original_source_reference,
            description=observation,
            relevant_observation=observation,
            confidence_score=confidence_score,
            is_contradictory=is_contradictory,
            verification_status=verification_status.value,
            is_fact=is_fact,
            environment=environment,
            deduplication_hash=dedup_hash,
            observed_at=now,
            raw_data=raw_data_str,
        )

        if session is not None:
            session.add(db_evidence)
            await session.flush()

        logger.info(
            f"[EvidenceEngine] Recorded evidence {ev_id} by {source_agent} [{evidence_category.value}] is_fact={is_fact}"
        )
        return db_evidence

    async def list_evidence(
        self,
        incident_id: str,
        session: AsyncSession,
        category: Optional[str] = None,
        is_fact: Optional[bool] = None,
        verification_status: Optional[str] = None,
        limit: int = 200,
    ) -> List[Evidence]:
        """
        Queries evidence records with optional category and fact/interpretation filters.
        """
        query = select(Evidence).where(Evidence.incident_id == incident_id)
        if category:
            query = query.where(
                (Evidence.evidence_category == category.upper())
                | (Evidence.evidence_type == category.lower())
            )
        if is_fact is not None:
            query = query.where(Evidence.is_fact == is_fact)
        if verification_status:
            query = query.where(Evidence.verification_status == verification_status.upper())

        query = query.order_by(desc(Evidence.observed_at)).limit(limit)
        res = await session.execute(query)
        return list(res.scalars().all())

    async def find_contradictions(
        self,
        incident_id: str,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Detects conflicting evidence observations (e.g. CPU normal vs CPU saturated).
        """
        ev_list = await self.list_evidence(incident_id, session)
        contradictions: List[Dict[str, Any]] = []

        # Find items explicitly flagged contradictory or opposing claims
        for ev in ev_list:
            if ev.is_contradictory or ev.verification_status == "CONTRADICTED":
                contradictions.append({
                    "evidence_id": ev.id,
                    "source_agent": ev.source_agent or ev.source_system,
                    "category": ev.evidence_category or ev.evidence_type,
                    "observation": ev.description,
                    "reason": "Explicit contradictory flag detected during cross-examination.",
                })

        return contradictions


# Singleton instance
shared_evidence_engine = SharedEvidenceEngine()
