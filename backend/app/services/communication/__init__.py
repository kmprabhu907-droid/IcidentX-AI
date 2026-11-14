"""
INCIDENTX AI - Real-Time On-Call Communication Engine (Phase 14)
"""

from backend.app.services.communication.schemas import (
    AcknowledgmentRecord,
    ChannelIntegrationConfig,
    ChatSenderType,
    CommunicationAnalytics,
    EscalationLevel,
    EscalationPolicy,
    EscalationState,
    IncidentChatMessage,
    IntegrationStatus,
    NotificationEventType,
    NotificationMessage,
    NotificationPriority,
    OnCallShift,
    TeamHandoffRecord,
)
from backend.app.services.communication.notification_service import (
    NotificationService,
    notification_service,
)

__all__ = [
    "AcknowledgmentRecord",
    "ChannelIntegrationConfig",
    "ChatSenderType",
    "CommunicationAnalytics",
    "EscalationLevel",
    "EscalationPolicy",
    "EscalationState",
    "IncidentChatMessage",
    "IntegrationStatus",
    "NotificationEventType",
    "NotificationMessage",
    "NotificationPriority",
    "OnCallShift",
    "TeamHandoffRecord",
    "NotificationService",
    "notification_service",
]
