"""
INCIDENTX AI - Remediation Pydantic Serialization Schemas
Defines request and response schemas for remediation actions, policies,
approvals, verification reports, and registry action descriptors.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RemediationActionResponse(BaseModel):
    id: str
    incident_id: str
    hypothesis_id: Optional[str] = None
    action_id: str
    name: str
    description: str
    action_type: str
    target_service_name: str
    parameters: Optional[str] = "{}"
    preconditions: Optional[str] = "[]"
    expected_outcome: Optional[str] = ""
    risk_level: str
    risk_tier: str
    estimated_cost: str
    expected_benefit: float
    recommendation_reason: Optional[str] = ""
    contraindications: Optional[str] = "[]"
    execution_mode: str
    idempotency_key: str
    timeout_seconds: int
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comment: Optional[str] = None
    status: str
    command_payload: Optional[str] = "{}"
    executed_at: Optional[datetime] = None
    execution_duration_ms: Optional[int] = None
    execution_log: Optional[str] = None
    snapshot_before: Optional[str] = None
    snapshot_after: Optional[str] = None
    verification_status: str
    verification_details: Optional[str] = None
    rollback_status: str
    rollback_log: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationPolicyResponse(BaseModel):
    id: str
    name: str
    mode: str
    is_autonomous_enabled: bool
    allowlisted_action_ids: str
    max_actions_per_incident: int
    max_retries: int
    cooldown_seconds: int
    circuit_breaker_tripped: bool
    circuit_breaker_reason: Optional[str] = None
    emergency_stop_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationPolicyUpdate(BaseModel):
    mode: Optional[str] = Field(None, description="RECOMMENDATION_ONLY, HUMAN_APPROVAL, or CONTROLLED_AUTONOMOUS")
    is_autonomous_enabled: Optional[bool] = None
    allowlisted_action_ids: Optional[List[str]] = None
    max_actions_per_incident: Optional[int] = Field(None, ge=1, le=10)


class ApproveActionRequest(BaseModel):
    approved_by: str = Field(..., min_length=2, max_length=100, description="Operator identifier")
    comment: Optional[str] = Field(None, max_length=500, description="Optional justification comment")


class RejectActionRequest(BaseModel):
    rejected_by: str = Field(..., min_length=2, max_length=100)
    reason: str = Field(..., min_length=3, max_length=500)


class EmergencyStopRequest(BaseModel):
    reason: str = Field(default="Manual operator emergency stop", min_length=3)
    requested_by: str = Field(default="operator", min_length=2)


class ActionRegistryItemResponse(BaseModel):
    action_id: str
    name: str
    description: str
    action_type: str
    supported_incident_types: List[str]
    risk_level: str
    estimated_cost: str
    timeout_seconds: int
    parameter_schema: Dict[str, Any]
