"""
INCIDENTX AI - Reliability Memory Interface
Provides structured abstraction for historical incident retrieval, confirmed root causes,
past remediation actions, verification histories, and recurring failure patterns.
Acts as the contract and integration point for Phase 5.4 Reliability Memory Engine.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.remediation import RemediationAction
from backend.app.models.telemetry import TelemetryEvent


class ReliabilityMemoryInterface(ABC):
    """Abstract interface defining the contract for Reliability Memory lookups."""

    @abstractmethod
    async def get_historical_incidents(
        self,
        service_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieves past incidents matching optional service and severity filters."""
        pass

    @abstractmethod
    async def get_confirmed_root_causes(
        self,
        service_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieves verified root causes and winning courtroom hypotheses."""
        pass

    @abstractmethod
    async def get_remediation_history(
        self,
        service_name: Optional[str] = None,
        action_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieves historical remediation actions and their execution records."""
        pass

    @abstractmethod
    async def get_rollback_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves actions that required operational rollbacks."""
        pass

    @abstractmethod
    async def get_recurring_metric_patterns(
        self,
        service_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieves recurring metric degradation patterns."""
        pass


class SqlAlchemyReliabilityMemory(ReliabilityMemoryInterface):
    """
    SQLAlchemy-backed implementation of ReliabilityMemoryInterface.
    Queries the actual relational tables (incidents, root_cause_hypotheses,
    evidence, remediation_actions, telemetry_events).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_historical_incidents(
        self,
        service_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = select(Incident).order_by(desc(Incident.detected_at)).limit(limit)
        if severity:
            query = query.where(Incident.severity == severity)
        
        result = await self.db.execute(query)
        incidents = result.scalars().all()

        results: List[Dict[str, Any]] = []
        for inc in incidents:
            # Check impact scope for service name match if filtered
            if service_name and inc.impact_scope and service_name not in inc.impact_scope:
                continue

            results.append({
                "id": inc.id,
                "title": inc.title,
                "summary": inc.summary or "",
                "severity": inc.severity,
                "status": inc.status,
                "detected_at": inc.detected_at.isoformat() if inc.detected_at else None,
                "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
                "impact_scope": inc.impact_scope or "",
                "mttr_seconds": inc.mttr_seconds,
            })
        return results

    async def get_confirmed_root_causes(
        self,
        service_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = (
            select(RootCauseHypothesis)
            .where(RootCauseHypothesis.status == "ACCEPTED")
            .order_by(desc(RootCauseHypothesis.created_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        hypotheses = result.scalars().all()

        return [
            {
                "id": h.id,
                "incident_id": h.incident_id,
                "culprit_service_id": h.culprit_service_id,
                "hypothesis_text": h.hypothesis_text,
                "probability_score": h.probability_score,
                "status": h.status,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in hypotheses
        ]

    async def get_remediation_history(
        self,
        service_name: Optional[str] = None,
        action_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = select(RemediationAction).order_by(desc(RemediationAction.created_at)).limit(limit)
        if service_name:
            query = query.where(RemediationAction.target_service_name == service_name)
        if action_id:
            query = query.where(RemediationAction.action_id == action_id)

        result = await self.db.execute(query)
        actions = result.scalars().all()

        return [
            {
                "id": a.id,
                "incident_id": a.incident_id,
                "action_id": a.action_id,
                "name": a.name,
                "target_service_name": a.target_service_name,
                "risk_level": a.risk_level,
                "status": a.status,
                "approval_status": a.approval_status,
                "verification_status": a.verification_status,
                "rollback_status": a.rollback_status,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "snapshot_before": a.snapshot_before,
                "snapshot_after": a.snapshot_after,
            }
            for a in actions
        ]

    async def get_rollback_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        query = (
            select(RemediationAction)
            .where(RemediationAction.rollback_status.in_(["EXECUTING", "ROLLED_BACK", "ROLLBACK_FAILED"]))
            .order_by(desc(RemediationAction.created_at))
            .limit(limit)
        )
        result = await self.db.execute(query)
        actions = result.scalars().all()

        return [
            {
                "id": a.id,
                "incident_id": a.incident_id,
                "action_id": a.action_id,
                "name": a.name,
                "target_service_name": a.target_service_name,
                "rollback_status": a.rollback_status,
                "rollback_log": a.rollback_log,
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
            }
            for a in actions
        ]

    async def get_recurring_metric_patterns(
        self,
        service_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query = (
            select(TelemetryEvent)
            .where(TelemetryEvent.event_type.in_(["metric_spike", "alert"]))
            .order_by(desc(TelemetryEvent.timestamp))
            .limit(limit)
        )
        result = await self.db.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": e.id,
                "incident_id": e.incident_id,
                "service_id": e.service_id,
                "metric_name": e.metric_name,
                "metric_value": e.metric_value,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ]
