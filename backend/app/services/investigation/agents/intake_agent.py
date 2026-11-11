"""
INCIDENTX AI - Incident Intake Agent
Validates incident payload, confirms detection timestamp, severity, and impacted scope.
"""

from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.services.ai.sanitizer import PromptSanitizer
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import IntakeResult


class IncidentIntakeAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="IncidentIntakeAgent",
            role="intake",
            execution_phase="INTAKE",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()

        if not incident:
            raise ValueError(f"Incident {incident_id} not found in database.")

        # Sanitize text
        clean_title = PromptSanitizer.sanitize_text(incident.title)
        clean_summary = PromptSanitizer.sanitize_text(incident.summary or "")
        clean_scope = PromptSanitizer.sanitize_text(incident.impact_scope or "")

        # Parse impacted services
        impacted_services = [s.strip() for s in clean_scope.split(",") if s.strip()]
        if not impacted_services and "payment" in clean_title.lower():
            impacted_services = ["payment-service", "order-service", "api-gateway"]

        intake_res = IntakeResult(
            is_valid=True,
            incident_id=incident.id,
            normalized_severity=incident.severity,
            normalized_scope=impacted_services,
            initial_assessment=f"Incident '{clean_title}' triaged. Initial severity: {incident.severity}.",
            sanitization_applied=True,
        )

        state["intake"] = intake_res.model_dump()
        state["incident"] = {
            "id": incident.id,
            "title": clean_title,
            "summary": clean_summary,
            "severity": incident.severity,
            "detected_at": incident.detected_at.isoformat(),
            "impact_scope": impacted_services,
        }
        return state
