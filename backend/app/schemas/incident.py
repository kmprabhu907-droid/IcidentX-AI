"""
INCIDENTX AI - Incident Pydantic Schemas (Phase 9)
Updated for Central Incident Lifecycle states (P1-P4, DETECTED through CLOSED/REOPENED),
ownership metadata, and real-time command center telemetry.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Incident title")
    summary: Optional[str] = Field(None, description="Detailed incident summary / description")
    severity: str = Field(
        default="P2",
        pattern="^(P1|P2|P3|P4|SEV-1|SEV-2|SEV-3|SEV-4)$",
        description="Severity tier (P1-P4 or SEV-1-4)",
    )
    status: str = Field(
        default="DETECTED",
        pattern="^(DETECTED|ACKNOWLEDGED|INVESTIGATING|ROOT_CAUSE_IDENTIFIED|REMEDIATION_PENDING|REMEDIATING|VERIFYING|RESOLVED|CLOSED|REOPENED|SUPPRESSED|CANCELLED|MITIGATING)$",
        description="Incident lifecycle status",
    )
    priority: Optional[str] = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    environment: Optional[str] = Field(default="DEMOMESH", description="DEMOMESH or KUBERNETES")
    source: Optional[str] = Field(default="MANUAL", description="Alert source: alertmanager, grafana, kubernetes, manual, webhook")
    impact_scope: Optional[str] = Field(None, max_length=255, description="Affected service or workload")
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    assigned_team: Optional[str] = "Platform SRE"
    oncall_responder: Optional[str] = "IncidentX AI (Tier-1)"


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    summary: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(P1|P2|P3|P4|SEV-1|SEV-2|SEV-3|SEV-4)$")
    status: Optional[str] = Field(None, pattern="^(DETECTED|ACKNOWLEDGED|INVESTIGATING|ROOT_CAUSE_IDENTIFIED|REMEDIATION_PENDING|REMEDIATING|VERIFYING|RESOLVED|CLOSED|REOPENED|SUPPRESSED|CANCELLED|MITIGATING)$")
    priority: Optional[str] = None
    environment: Optional[str] = None
    source: Optional[str] = None
    impact_scope: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    assigned_team: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None


class IncidentTransitionRequest(BaseModel):
    target_state: str = Field(..., description="Target lifecycle state")
    actor: str = Field(default="sre-operator", description="Actor triggering state change")
    actor_type: str = Field(default="HUMAN", description="HUMAN, AI_AGENT, SYSTEM")
    reason: Optional[str] = Field(None, description="Operational justification for state change")


class IncidentAssignRequest(BaseModel):
    assigned_to_id: str
    assigned_to_name: str
    team_name: str = "Platform SRE"
    assigned_by: str = "sre-lead@enterprise.io"
    role: str = "PRIMARY_RESPONDER"
    reason: Optional[str] = None


class IncidentReassignRequest(BaseModel):
    new_owner_id: str
    new_owner_name: str
    new_team_name: str = "Platform SRE"
    assigned_by: str = "sre-lead@enterprise.io"
    reason: str = "Shift rotation / specialization handoff"


class IncidentAcknowledgeRequest(BaseModel):
    responder_id: str = "user-sre-1"
    responder_name: str = "Primary On-Call SRE"


class IncidentEscalateRequest(BaseModel):
    reason: str
    target_tier: str = "ESCALATED_TIER_2"
    escalated_by: str = "oncall-operator"


class IncidentResponse(IncidentBase):
    id: str
    fingerprint: Optional[str] = None
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None
    is_escalated: bool = False
    escalation_status: str = "NORMAL"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentStatisticsResponse(BaseModel):
    total_active: int
    p1_critical: int
    p2_high: int
    p3_medium: int
    p4_low: int
    investigating: int
    unassigned: int
    resolved_count: int
    mean_time_to_acknowledge_seconds: float
    mean_time_to_resolve_seconds: float
    environment_counts: Dict[str, int]


class TimelineEventResponse(BaseModel):
    id: str
    incident_id: str
    timestamp: datetime
    event_type: str
    service_name: str
    title: str
    description: str
    severity: str
    actor: str
    actor_type: str
    data_source: str
    raw_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentAssignmentItem(BaseModel):
    id: str
    assigned_to_id: str
    assigned_to_name: str
    team_name: str
    assigned_by: str
    role: str
    reason: Optional[str] = None
    created_at: Optional[str] = None


class IncidentOwnershipSummaryResponse(BaseModel):
    incident_id: str
    owner_id: Optional[str] = None
    owner_name: str
    assigned_team: str
    oncall_responder: str
    is_acknowledged: bool
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    time_since_detection_seconds: float
    time_since_acknowledgement_seconds: Optional[float] = None
    is_escalated: bool
    escalation_status: str
    escalation_deadline: Optional[str] = None
    assignment_history: List[IncidentAssignmentItem] = Field(default_factory=list)
