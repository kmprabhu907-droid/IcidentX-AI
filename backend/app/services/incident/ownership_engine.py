"""
INCIDENTX AI - Incident Ownership & Escalation Engine (Phase 9 Module 9.4)
Manages primary responder assignment, team-based ownership, reassignments,
escalation deadlines, SLA tracking, and assignment history.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.incident_assignment import IncidentAssignment
from backend.app.services.agents.oncall_agent import oncall_incident_agent
from backend.app.services.incident.lifecycle_engine import incident_lifecycle_engine
from backend.app.services.incident.timeline_engine import incident_timeline_engine


class IncidentOwnershipEngine:
    """
    Central controller for incident assignment, team ownership, and escalation policies.
    """

    @classmethod
    async def assign_owner(
        cls,
        incident_id: str,
        assigned_to_id: str,
        assigned_to_name: str,
        team_name: str = "Platform SRE",
        assigned_by: str = "SYSTEM",
        role: str = "PRIMARY_RESPONDER",
        reason: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Incident:
        now = datetime.now(timezone.utc)
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise IncidentXException(f"Incident '{incident_id}' not found.", status_code=404)

        prev_owner = incident.owner_name or "Unassigned"
        incident.owner_id = assigned_to_id
        incident.owner_name = assigned_to_name
        incident.assigned_team = team_name
        incident.updated_at = now

        # Record assignment record
        assignment = IncidentAssignment(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            assigned_to_id=assigned_to_id,
            assigned_to_name=assigned_to_name,
            team_name=team_name,
            assigned_by=assigned_by,
            role=role,
            reason=reason,
            created_at=now,
        )
        session.add(assignment)

        # Timeline Event
        desc_text = (
            f"Assigned to {assigned_to_name} ({team_name}) as {role} by {assigned_by}."
        )
        if reason:
            desc_text += f" Reason: {reason}"

        await incident_timeline_engine.record_event(
            incident_id=incident.id,
            event_type="ONCALL_ASSIGNED",
            service_name=incident.impact_scope or "cluster",
            title=f"Owner Assigned: {assigned_to_name}",
            description=desc_text,
            severity="INFO",
            actor=assigned_by,
            actor_type="HUMAN" if "user:" in assigned_by or "@" in assigned_by else "SYSTEM",
            data_source=incident.environment or "LIVE",
            session=session,
        )

        # Audit Log
        audit = AuditLog(
            incident_id=incident.id,
            organization_id=incident.organization_id or "default-org",
            actor_type="USER",
            actor_id=assigned_by,
            action="INCIDENT_ASSIGNED",
            resource_type="Incident",
            resource_id=incident.id,
            details=f"Assigned incident to {assigned_to_name} ({team_name}). Previous: {prev_owner}.",
        )
        session.add(audit)

        logger.info(f"[OwnershipEngine] Incident {incident_id} assigned to {assigned_to_name} by {assigned_by}")
        return incident

    @classmethod
    async def reassign_owner(
        cls,
        incident_id: str,
        new_owner_id: str,
        new_owner_name: str,
        new_team_name: str,
        assigned_by: str,
        reason: str,
        session: AsyncSession,
    ) -> Incident:
        return await cls.assign_owner(
            incident_id=incident_id,
            assigned_to_id=new_owner_id,
            assigned_to_name=new_owner_name,
            team_name=new_team_name,
            assigned_by=assigned_by,
            role="PRIMARY_RESPONDER",
            reason=reason,
            session=session,
        )

    @classmethod
    async def acknowledge_incident(
        cls,
        incident_id: str,
        responder_id: str,
        responder_name: str,
        session: AsyncSession,
    ) -> Incident:
        now = datetime.now(timezone.utc)
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise IncidentXException(f"Incident '{incident_id}' not found.", status_code=404)

        if incident.status == "DETECTED":
            incident.status = "ACKNOWLEDGED"

        incident.acknowledged_at = now
        incident.acknowledged_by = responder_name
        incident.updated_at = now

        # Timeline Event
        await incident_timeline_engine.record_event(
            incident_id=incident.id,
            event_type="ACKNOWLEDGED",
            service_name=incident.impact_scope or "cluster",
            title=f"Acknowledged by {responder_name}",
            description=f"Incident acknowledged by responder '{responder_name}' (ID: {responder_id}).",
            severity="INFO",
            actor=responder_name,
            actor_type="HUMAN" if "@" in responder_name or "user:" in responder_id else "AI_AGENT",
            data_source=incident.environment or "LIVE",
            session=session,
        )

        logger.info(f"[OwnershipEngine] Incident {incident_id} acknowledged by {responder_name}")
        return incident

    @classmethod
    async def escalate_incident(
        cls,
        incident_id: str,
        reason: str,
        target_tier: str = "ESCALATED_TIER_2",
        escalated_by: str = "oncall-operator",
        session: Optional[AsyncSession] = None,
    ) -> Incident:
        now = datetime.now(timezone.utc)
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise IncidentXException(f"Incident '{incident_id}' not found.", status_code=404)

        incident.is_escalated = True
        incident.escalation_status = target_tier
        incident.updated_at = now

        # Timeline Event
        await incident_timeline_engine.record_event(
            incident_id=incident.id,
            event_type="ESCALATED",
            service_name=incident.impact_scope or "cluster",
            title=f"Escalated to {target_tier}",
            description=f"Escalation triggered by {escalated_by}. Reason: {reason}",
            severity="WARN",
            actor=escalated_by,
            actor_type="HUMAN",
            data_source=incident.environment or "LIVE",
            session=session,
        )

        # Notify On-Call Agent
        try:
            await oncall_incident_agent.escalate_to_human(
                page_id=incident.id,
                reason=reason,
            )
        except Exception as e:
            logger.debug(f"[OwnershipEngine] On-call agent escalation note: {e}")

        logger.warning(f"[OwnershipEngine] Incident {incident_id} escalated to {target_tier}. Reason: {reason}")
        return incident

    @classmethod
    async def get_ownership_summary(
        cls,
        incident_id: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise IncidentXException(f"Incident '{incident_id}' not found.", status_code=404)

        # Fetch assignment history
        assign_stmt = (
            select(IncidentAssignment)
            .where(IncidentAssignment.incident_id == incident_id)
            .order_by(desc(IncidentAssignment.created_at))
        )
        assign_res = await session.execute(assign_stmt)
        assignments = list(assign_res.scalars().all())

        det = (
            incident.detected_at.replace(tzinfo=timezone.utc)
            if (incident.detected_at and incident.detected_at.tzinfo is None)
            else incident.detected_at
        )
        ack = (
            incident.acknowledged_at.replace(tzinfo=timezone.utc)
            if (incident.acknowledged_at and incident.acknowledged_at.tzinfo is None)
            else incident.acknowledged_at
        )
        time_since_detection = (now - det).total_seconds() if det else 0
        time_since_ack = (now - ack).total_seconds() if ack else None

        return {
            "incident_id": incident.id,
            "owner_id": incident.owner_id,
            "owner_name": incident.owner_name or "Unassigned",
            "assigned_team": incident.assigned_team or "Platform SRE",
            "oncall_responder": incident.oncall_responder or "IncidentX AI (Tier-1)",
            "is_acknowledged": incident.acknowledged_at is not None,
            "acknowledged_at": incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
            "acknowledged_by": incident.acknowledged_by,
            "time_since_detection_seconds": round(time_since_detection, 1),
            "time_since_acknowledgement_seconds": round(time_since_ack, 1) if time_since_ack is not None else None,
            "is_escalated": incident.is_escalated,
            "escalation_status": incident.escalation_status,
            "escalation_deadline": incident.escalation_deadline.isoformat() if incident.escalation_deadline else None,
            "assignment_history": [
                {
                    "id": a.id,
                    "assigned_to_id": a.assigned_to_id,
                    "assigned_to_name": a.assigned_to_name,
                    "team_name": a.team_name,
                    "assigned_by": a.assigned_by,
                    "role": a.role,
                    "reason": a.reason,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in assignments
            ],
        }


# Singleton engine
incident_ownership_engine = IncidentOwnershipEngine()
