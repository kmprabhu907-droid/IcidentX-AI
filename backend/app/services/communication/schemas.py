"""
INCIDENTX AI - Real-Time On-Call Communication Engine Schemas (Phase 14)
Data contracts for notification routing, on-call schedules, multi-tier escalation,
acknowledgment, team handoffs, incident rooms, and delivery integrations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationEventType(str, Enum):
    INCIDENT_DETECTED = "INCIDENT_DETECTED"
    SEV1_CRITICAL = "SEV1_CRITICAL"
    INCIDENT_ASSIGNED = "INCIDENT_ASSIGNED"
    INCIDENT_ACKNOWLEDGED = "INCIDENT_ACKNOWLEDGED"
    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    REMEDIATION_APPROVAL_REQUESTED = "REMEDIATION_APPROVAL_REQUESTED"
    REMEDIATION_STARTED = "REMEDIATION_STARTED"
    REMEDIATION_FAILED = "REMEDIATION_FAILED"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    INCIDENT_REOPENED = "INCIDENT_REOPENED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"


class NotificationPriority(str, Enum):
    P1_URGENT = "P1_URGENT"
    P2_HIGH = "P2_HIGH"
    P3_NORMAL = "P3_NORMAL"
    P4_LOW = "P4_LOW"


class NotificationMessage(BaseModel):
    """Normalized incident notification payload."""
    notification_id: str
    incident_id: str
    event_type: NotificationEventType
    priority: NotificationPriority
    severity: str
    title: str
    affected_service: str
    summary: str
    assigned_team: str = "Core SRE"
    required_action: str
    incident_url: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_channels: List[str] = Field(default_factory=list)
    dedup_key: str = ""
    status: str = "DELIVERED"  # PENDING, DELIVERED, DEDUPED, FAILED


class OnCallShift(BaseModel):
    """Active on-call roster shift."""
    shift_id: str
    team_name: str
    primary_responder: str
    primary_email: str
    secondary_responder: str
    secondary_email: str
    escalation_lead: str
    timezone: str = "UTC"
    shift_start: datetime
    shift_end: datetime
    is_active: bool = True
    override_active: bool = False
    override_notes: Optional[str] = None


class EscalationLevel(BaseModel):
    """Step in an escalation policy."""
    step_number: int
    role_target: str       # PRIMARY, SECONDARY, ESCALATION_TEAM, INCIDENT_COMMANDER
    timeout_minutes: int
    notification_channel: str = "PAGER_AND_SLACK"


class EscalationPolicy(BaseModel):
    """Configurable escalation matrix."""
    policy_id: str
    name: str
    severity: str          # SEV-1, SEV-2, SEV-3
    service_name: Optional[str] = None
    levels: List[EscalationLevel]
    is_active: bool = True


class EscalationState(BaseModel):
    """Live state of an incident escalation."""
    incident_id: str
    current_level: int = 1
    escalation_count: int = 0
    next_deadline: datetime
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    escalation_log: List[Dict[str, Any]] = Field(default_factory=list)


class AcknowledgmentRecord(BaseModel):
    """Record of incident acknowledgment."""
    acknowledgment_id: str
    incident_id: str
    responder_id: str
    responder_role: str
    accepted: bool = True
    rejection_reason: Optional[str] = None
    time_to_acknowledge_seconds: float = 0.0
    acknowledged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamHandoffRecord(BaseModel):
    """Structured shift and incident handoff briefing."""
    handoff_id: str
    incident_id: str
    from_responder: str
    to_responder: str
    handoff_type: str = "SHIFT_ROTATION"  # SHIFT_ROTATION, ESCALATION_HANDOFF, COMMANDER_REASSIGNMENT
    
    incident_summary: str
    current_severity: str
    investigation_progress: str
    confirmed_root_cause: Optional[str] = None
    competing_hypotheses: List[str] = Field(default_factory=list)
    completed_actions: List[str] = Field(default_factory=list)
    pending_approvals: List[str] = Field(default_factory=list)
    remediation_status: str = "PENDING"
    recovery_verification_status: str = "NOT_STARTED"
    outstanding_risks: List[str] = Field(default_factory=list)
    next_recommended_actions: List[str] = Field(default_factory=list)
    transferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSenderType(str, Enum):
    HUMAN = "HUMAN"
    AI_AGENT = "AI_AGENT"
    SYSTEM = "SYSTEM"


class IncidentChatMessage(BaseModel):
    """Message inside the shared incident war room."""
    message_id: str
    incident_id: str
    sender_name: str
    sender_type: ChatSenderType
    sender_role: str = "Responder"
    content: str
    is_pinned: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IntegrationStatus(str, Enum):
    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTIVITY_ERROR = "CONNECTIVITY_ERROR"


class ChannelIntegrationConfig(BaseModel):
    """Configuration for Slack, Teams, Email, or Webhooks."""
    channel_name: str  # Slack, Teams, Email, Webhook
    status: IntegrationStatus = IntegrationStatus.NOT_CONFIGURED
    endpoint_masked: str = ""
    is_enabled: bool = False
    last_tested_at: Optional[datetime] = None
    last_test_success: bool = False


class CommunicationAnalytics(BaseModel):
    """High-level team response metrics."""
    mean_time_to_acknowledge_seconds: float = 0.0
    mean_time_to_assign_seconds: float = 0.0
    total_notifications_sent: int = 0
    delivery_success_rate: float = 1.0
    unacknowledged_incidents_count: int = 0
    handoffs_completed_count: int = 0
    active_responders_count: int = 0
