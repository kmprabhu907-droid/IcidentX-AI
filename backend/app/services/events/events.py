"""
INCIDENTX AI - Strongly-Typed Domain Event Definitions (Stage 6.5)
Implements CloudEvents 1.0 specification compliant reliability domain events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base CloudEvent 1.0 envelope for IncidentX domain events."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "ai.incidentx.control-plane"
    specversion: str = "1.0"
    type: str
    time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    organization_id: str = "default-org"
    data: Dict[str, Any] = Field(default_factory=dict)


class IncidentDetectedEvent(DomainEvent):
    type: str = "ai.incidentx.incident.detected"


class RootCauseIdentifiedEvent(DomainEvent):
    type: str = "ai.incidentx.investigation.root_cause_identified"


class RemediationRequestedEvent(DomainEvent):
    type: str = "ai.incidentx.remediation.approval_requested"


class RemediationApprovedEvent(DomainEvent):
    type: str = "ai.incidentx.remediation.approved"


class RemediationExecutedEvent(DomainEvent):
    type: str = "ai.incidentx.remediation.executed"


class RegressionDetectedEvent(DomainEvent):
    type: str = "ai.incidentx.observability.regression_detected"


class SLOBudgetBurnExceededEvent(DomainEvent):
    type: str = "ai.incidentx.slo.burn_rate_exceeded"
