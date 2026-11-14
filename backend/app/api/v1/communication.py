"""
INCIDENTX AI - Real-Time On-Call Communication API Endpoints (Phase 14)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.app.services.communication.notification_service import notification_service
from backend.app.services.communication.schemas import (
    AcknowledgmentRecord,
    ChannelIntegrationConfig,
    ChatSenderType,
    CommunicationAnalytics,
    EscalationState,
    IncidentChatMessage,
    NotificationEventType,
    NotificationMessage,
    OnCallShift,
    TeamHandoffRecord,
)

router = APIRouter(prefix="/communication", tags=["Real-Time On-Call Communication (Phase 14)"])


class SendNotificationRequest(BaseModel):
    incident_id: str
    event_type: NotificationEventType
    severity: str = "SEV-1"
    title: str
    affected_service: str
    summary: str
    assigned_team: str = "Core SRE"
    required_action: str = "Acknowledge in incident console"


class ShiftOverrideRequest(BaseModel):
    override_responder: str
    reason: str


class AcknowledgeRequest(BaseModel):
    responder_id: str
    responder_role: str = "Primary On-Call"
    accepted: bool = True
    rejection_reason: Optional[str] = None


class HandoffRequest(BaseModel):
    from_responder: str
    to_responder: str
    incident_summary: str
    current_severity: str = "SEV-1"
    investigation_progress: str
    confirmed_root_cause: Optional[str] = None
    remediation_status: str = "IN_PROGRESS"
    outstanding_risks: Optional[List[str]] = None
    next_recommended_actions: Optional[List[str]] = None


class ChatPostRequest(BaseModel):
    sender_name: str
    sender_type: ChatSenderType = ChatSenderType.HUMAN
    content: str
    is_pinned: bool = False


class IntegrationConfigRequest(BaseModel):
    endpoint_or_webhook: str
    is_enabled: bool = True


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/notifications", response_model=NotificationMessage)
async def send_notification(payload: SendNotificationRequest):
    return notification_service.send_incident_notification(
        incident_id=payload.incident_id,
        event_type=payload.event_type,
        severity=payload.severity,
        title=payload.title,
        affected_service=payload.affected_service,
        summary=payload.summary,
        assigned_team=payload.assigned_team,
        required_action=payload.required_action,
    )


@router.get("/notifications", response_model=List[NotificationMessage])
async def list_notifications(incident_id: Optional[str] = Query(None)):
    return notification_service.list_notifications(incident_id)


@router.get("/shifts", response_model=List[OnCallShift])
async def list_shifts():
    return notification_service.list_shifts()


@router.get("/shifts/active", response_model=Optional[OnCallShift])
async def get_active_shift(team: str = Query("Core SRE")):
    return notification_service.get_active_shift(team)


@router.post("/shifts/{shift_id}/override", response_model=OnCallShift)
async def set_shift_override(shift_id: str, payload: ShiftOverrideRequest):
    shift = notification_service.set_shift_override(shift_id, payload.override_responder, payload.reason)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


@router.post("/incidents/{incident_id}/escalate", response_model=EscalationState)
async def check_escalate(incident_id: str):
    return notification_service.check_and_escalate(incident_id)


@router.get("/incidents/{incident_id}/escalation", response_model=Optional[EscalationState])
async def get_escalation(incident_id: str):
    state = notification_service.get_escalation_state(incident_id)
    if not state:
        raise HTTPException(status_code=404, detail="No escalation state for incident")
    return state


@router.post("/incidents/{incident_id}/acknowledge", response_model=AcknowledgmentRecord)
async def acknowledge_incident(incident_id: str, payload: AcknowledgeRequest):
    return notification_service.acknowledge_incident(
        incident_id=incident_id,
        responder_id=payload.responder_id,
        responder_role=payload.responder_role,
        accepted=payload.accepted,
        rejection_reason=payload.rejection_reason,
    )


@router.post("/incidents/{incident_id}/handoff", response_model=TeamHandoffRecord)
async def create_handoff(incident_id: str, payload: HandoffRequest):
    return notification_service.perform_handoff(
        incident_id=incident_id,
        from_responder=payload.from_responder,
        to_responder=payload.to_responder,
        incident_summary=payload.incident_summary,
        current_severity=payload.current_severity,
        investigation_progress=payload.investigation_progress,
        confirmed_root_cause=payload.confirmed_root_cause,
        remediation_status=payload.remediation_status,
        outstanding_risks=payload.outstanding_risks,
        next_recommended_actions=payload.next_recommended_actions,
    )


@router.get("/incidents/{incident_id}/handoffs", response_model=List[TeamHandoffRecord])
async def list_handoffs(incident_id: str):
    return notification_service.list_handoffs(incident_id)


@router.post("/incidents/{incident_id}/chat", response_model=IncidentChatMessage)
async def post_chat(incident_id: str, payload: ChatPostRequest):
    return notification_service.post_chat_message(
        incident_id=incident_id,
        sender_name=payload.sender_name,
        sender_type=payload.sender_type,
        content=payload.content,
        is_pinned=payload.is_pinned,
    )


@router.get("/incidents/{incident_id}/chat", response_model=List[IncidentChatMessage])
async def get_chat(incident_id: str):
    return notification_service.get_chat_messages(incident_id)


@router.get("/integrations", response_model=List[ChannelIntegrationConfig])
async def list_integrations():
    return notification_service.list_integrations()


@router.post("/integrations/{channel_name}", response_model=ChannelIntegrationConfig)
async def configure_integration(channel_name: str, payload: IntegrationConfigRequest):
    return notification_service.configure_integration(
        channel_name=channel_name,
        endpoint_or_webhook=payload.endpoint_or_webhook,
        is_enabled=payload.is_enabled,
    )


@router.get("/analytics", response_model=CommunicationAnalytics)
async def get_analytics():
    return notification_service.get_analytics()
