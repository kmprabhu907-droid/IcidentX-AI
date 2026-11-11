"""
INCIDENTX AI - Integration Pydantic Schemas (Stage 6.4)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.integration import IntegrationProvider


class IntegrationConfigCreateRequest(BaseModel):
    provider: IntegrationProvider
    name: str = Field(..., min_length=2, max_length=100)
    is_enabled: bool = True
    config_dict: Dict[str, Any] = Field(default_factory=dict)
    events_subscribed: List[str] = Field(
        default=[
            "INCIDENT_DETECTED",
            "RCA_COMPLETED",
            "REMEDIATION_APPROVAL_REQUESTED",
            "REMEDIATION_EXECUTED",
            "REGRESSION_DETECTED",
        ]
    )


class IntegrationConfigUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    config_dict: Optional[Dict[str, Any]] = None
    events_subscribed: Optional[List[str]] = None


class IntegrationConfigResponse(BaseModel):
    id: str
    organization_id: str
    provider: str
    name: str
    is_enabled: bool
    events_subscribed: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IntegrationTestResponse(BaseModel):
    status: str
    message: str
    provider: str


class EventDispatchTestRequest(BaseModel):
    event_type: str = "INCIDENT_DETECTED"
    severity: str = "SEV-1"
    service_name: str = "payment-gateway"
    title: str = "Synthetic Test Incident Triggered"
    root_cause: Optional[str] = "Simulated cascading connection starvation in downstream service"
    confidence: float = 0.94
    action_name: Optional[str] = "Restart Connection Pool"
