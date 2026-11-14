"""
INCIDENTX AI - Central Incident Lifecycle Engine (Phase 9 Module 9.1)
Manages incident lifecycle states, validates state transitions, enforces severity tiers,
computes resolution metrics, and generates immutable transition timeline and audit entries.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.timeline import TimelineEvent
from backend.app.services.incident.timeline_engine import incident_timeline_engine


class IncidentLifecycleState(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    REMEDIATION_PENDING = "REMEDIATION_PENDING"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"
    SUPPRESSED = "SUPPRESSED"
    CANCELLED = "CANCELLED"


class IncidentSeverity(str, Enum):
    P1 = "P1"  # Critical: Service Outage / Customer Data / Revenue Loss
    P2 = "P2"  # High: Core Feature Degraded / Workaround Needed
    P3 = "P3"  # Medium: Minor Performance Anomaly / Non-Critical
    P4 = "P4"  # Low: Informational / Minor Alert


SEVERITY_MAPPING: Dict[str, str] = {
    "SEV-1": "P1",
    "SEV-2": "P2",
    "SEV-3": "P3",
    "SEV-4": "P4",
    "P1": "P1",
    "P2": "P2",
    "P3": "P3",
    "P4": "P4",
    "CRITICAL": "P1",
    "HIGH": "P2",
    "MEDIUM": "P3",
    "LOW": "P4",
    "INFO": "P4",
}


class InvalidLifecycleTransitionException(IncidentXException):
    def __init__(self, current_state: str, target_state: str, allowed: Set[str]):
        msg = (
            f"Invalid incident lifecycle transition from '{current_state}' to '{target_state}'. "
            f"Allowed next states: {sorted(list(allowed))}."
        )
        super().__init__(message=msg, status_code=400)


class IncidentLifecycleEngine:
    """
    State machine controller enforcing safe, valid lifecycle transitions.
    """

    # Valid State Transition Matrix
    VALID_TRANSITIONS: Dict[str, Set[str]] = {
        "DETECTED": {"ACKNOWLEDGED", "INVESTIGATING", "SUPPRESSED", "CANCELLED"},
        "ACKNOWLEDGED": {"INVESTIGATING", "SUPPRESSED", "CANCELLED", "RESOLVED"},
        "INVESTIGATING": {"ROOT_CAUSE_IDENTIFIED", "REMEDIATION_PENDING", "RESOLVED", "CANCELLED"},
        "ROOT_CAUSE_IDENTIFIED": {"REMEDIATION_PENDING", "REMEDIATING", "INVESTIGATING", "RESOLVED"},
        "REMEDIATION_PENDING": {"REMEDIATING", "INVESTIGATING", "CANCELLED", "RESOLVED"},
        "REMEDIATING": {"VERIFYING", "INVESTIGATING", "REMEDIATION_PENDING", "RESOLVED"},
        "VERIFYING": {"RESOLVED", "INVESTIGATING", "REMEDIATING", "REMEDIATION_PENDING"},
        "RESOLVED": {"CLOSED", "REOPENED"},
        "CLOSED": {"REOPENED"},
        "REOPENED": {"ACKNOWLEDGED", "INVESTIGATING"},
        "SUPPRESSED": {"ACKNOWLEDGED", "CLOSED", "CANCELLED"},
        "CANCELLED": {"REOPENED"},
    }

    @classmethod
    def normalize_severity(cls, raw_severity: Optional[str]) -> str:
        if not raw_severity:
            return "P2"
        return SEVERITY_MAPPING.get(raw_severity.upper(), "P2")

    @classmethod
    def validate_transition(cls, current_state: str, target_state: str) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(current_state.upper(), set())
        return target_state.upper() in allowed

    @classmethod
    async def transition(
        cls,
        incident_id: str,
        target_state: str,
        actor: str = "SYSTEM",
        actor_type: str = "SYSTEM",
        reason: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Incident:
        """
        Executes a validated lifecycle transition and records timeline + audit events.
        """
        target_norm = target_state.upper()
        now = datetime.now(timezone.utc)

        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise IncidentXException(f"Incident '{incident_id}' not found.", status_code=404)

        current_norm = incident.status.upper()

        # Idempotent no-op if already in target state
        if current_norm == target_norm:
            return incident

        allowed = cls.VALID_TRANSITIONS.get(current_norm, set())
        if target_norm not in allowed:
            raise InvalidLifecycleTransitionException(current_norm, target_norm, allowed)

        prev_state = incident.status
        incident.status = target_norm
        incident.updated_at = now

        # Timestamp logic
        if target_norm == "ACKNOWLEDGED":
            if not incident.acknowledged_at:
                incident.acknowledged_at = now
                incident.acknowledged_by = actor
        elif target_norm == "RESOLVED":
            incident.resolved_at = now
            if incident.detected_at:
                det = (
                    incident.detected_at.replace(tzinfo=timezone.utc)
                    if incident.detected_at.tzinfo is None
                    else incident.detected_at
                )
                incident.mttr_seconds = (now - det).total_seconds()
        elif target_norm == "CLOSED":
            incident.closed_at = now
        elif target_norm == "REOPENED":
            incident.resolved_at = None
            incident.closed_at = None

        # Record Timeline Event & Broadcast via SSE
        desc = (
            f"Incident transitioned from '{prev_state}' to '{target_norm}' by {actor} ({actor_type})."
        )
        if reason:
            desc += f" Reason: {reason}"

        await incident_timeline_engine.record_event(
            incident_id=incident.id,
            event_type="LIFECYCLE_TRANSITION",
            service_name=incident.impact_scope or "cluster",
            title=f"Status Changed: {target_norm}",
            description=desc,
            severity="INFO" if target_norm in ["RESOLVED", "CLOSED"] else "WARN",
            actor=actor,
            actor_type=actor_type,
            data_source=incident.environment or "LIVE",
            raw_data=f'{{"previous_state": "{prev_state}", "target_state": "{target_norm}", "reason": "{reason or ""}"}}',
            session=session,
        )

        # Record Audit Log
        audit_entry = AuditLog(
            incident_id=incident.id,
            organization_id=incident.organization_id or "default-org",
            actor_type=actor_type,
            actor_id=actor,
            action=f"INCIDENT_STATUS_{target_norm}",
            resource_type="Incident",
            resource_id=incident.id,
            details=desc,
        )
        session.add(audit_entry)

        logger.info(
            f"[IncidentLifecycleEngine] Incident {incident_id} transitioned: {prev_state} -> {target_norm} by {actor}"
        )
        return incident


# Singleton instance
incident_lifecycle_engine = IncidentLifecycleEngine()
