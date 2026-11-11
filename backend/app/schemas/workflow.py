"""
INCIDENTX AI - Workflow Pydantic Schemas (Stage 6.5)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorkflowTriggerRequest(BaseModel):
    incident_id: Optional[str] = None
    service_name: str = Field(default="order-service")
    severity: str = Field(default="SEV-2")
    title: str = Field(default="Autonomous Reliability Workflow Execution")
    auto_approve: bool = Field(
        default=False,
        description="Whether to automatically execute remediation without pausing for human sign-off"
    )


class WorkflowResumeRequest(BaseModel):
    approved: bool = Field(..., description="True to authorize remediation; False to reject")
    comment: Optional[str] = Field(default=None, description="Operator authorization rationale")


class WorkflowStepItem(BaseModel):
    step: str
    status: str
    timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    incident_id: Optional[str] = None
    workflow_type: str
    status: str
    current_step: str
    step_history: List[WorkflowStepItem]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
