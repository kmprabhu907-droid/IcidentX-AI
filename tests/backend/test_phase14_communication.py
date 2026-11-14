"""
INCIDENTX AI - Phase 14 Comprehensive Test Suite (On-Call Communication Engine)
"""

import pytest
from datetime import datetime, timezone

from backend.app.services.communication.schemas import (
    ChatSenderType,
    NotificationEventType,
    NotificationPriority,
)
from backend.app.services.communication.notification_service import NotificationService


def test_notification_dispatch_and_deduplication():
    svc = NotificationService()
    
    # 1. Send first notification
    n1 = svc.send_incident_notification(
        incident_id="INC-P14-001",
        event_type=NotificationEventType.SEV1_CRITICAL,
        severity="SEV-1",
        title="Payment Service Critical Outage",
        affected_service="payment-service",
        summary="HTTP 5xx rate exceeded 25%",
    )
    assert n1.status == "DELIVERED"
    assert n1.priority == NotificationPriority.P1_URGENT
    assert "CONSOLE_TIMELINE" in n1.delivered_channels

    # 2. Send duplicate notification within 60s
    n2 = svc.send_incident_notification(
        incident_id="INC-P14-001",
        event_type=NotificationEventType.SEV1_CRITICAL,
        severity="SEV-1",
        title="Payment Service Critical Outage (Retry)",
        affected_service="payment-service",
        summary="HTTP 5xx rate exceeded 25%",
    )
    assert n2.status == "DEDUPED"


def test_oncall_schedule_and_override():
    svc = NotificationService()
    shift = svc.get_active_shift("Core SRE")
    assert shift is not None
    assert "Sarah Chen" in shift.primary_responder

    # Apply manual override
    updated = svc.set_shift_override(
        shift_id=shift.shift_id,
        override_responder="Elena Rostova (Senior SRE)",
        reason="Primary responder medical leave",
    )
    assert updated is not None
    assert updated.override_active is True
    assert updated.primary_responder == "Elena Rostova (Senior SRE)"


def test_escalation_lifecycle_and_acknowledgment():
    svc = NotificationService()
    incident_id = "INC-P14-002"

    # Initiate escalation
    esc = svc.initiate_escalation(incident_id, "SEV-1")
    assert esc.current_level == 1
    assert esc.is_acknowledged is False

    # Simulate timeout check
    esc_updated = svc.check_and_escalate(incident_id)
    assert esc_updated.incident_id == incident_id

    # Acknowledge incident
    ack = svc.acknowledge_incident(
        incident_id=incident_id,
        responder_id="sarah.chen",
        responder_role="Primary On-Call",
        accepted=True,
    )
    assert ack.accepted is True
    assert ack.time_to_acknowledge_seconds > 0

    # Verify escalation halted
    final_esc = svc.get_escalation_state(incident_id)
    assert final_esc.is_acknowledged is True
    assert final_esc.acknowledged_by == "sarah.chen"


def test_team_handoff_briefing():
    svc = NotificationService()
    hnd = svc.perform_handoff(
        incident_id="INC-P14-003",
        from_responder="Sarah Chen",
        to_responder="Marcus Vance",
        incident_summary="Payment service memory leak under control post-rollback",
        current_severity="SEV-2",
        investigation_progress="Root cause verified as unbounded transaction cache",
        confirmed_root_cause="JVM heap exhaustion",
        remediation_status="COMPLETED",
    )
    assert hnd.from_responder == "Sarah Chen"
    assert hnd.to_responder == "Marcus Vance"
    assert len(hnd.next_recommended_actions) >= 1
    assert len(svc.list_handoffs("INC-P14-003")) == 1


def test_incident_war_room_chat():
    svc = NotificationService()
    msg = svc.post_chat_message(
        incident_id="INC-P14-004",
        sender_name="Incident Commander",
        sender_type=ChatSenderType.HUMAN,
        content="War room opened. P1 rollback approved.",
        is_pinned=True,
    )
    assert msg.is_pinned is True
    assert msg.sender_type == ChatSenderType.HUMAN

    messages = svc.get_chat_messages("INC-P14-004")
    assert len(messages) >= 1


def test_integrations_and_analytics():
    svc = NotificationService()
    integrations = svc.list_integrations()
    assert len(integrations) >= 2

    # Configure new webhook
    cfg = svc.configure_integration(
        channel_name="Custom Webhook",
        endpoint_or_webhook="https://api.internal.corp/incident-webhook",
        is_enabled=True,
    )
    assert cfg.status.value == "CONFIGURED"
    assert cfg.last_test_success is True

    # Analytics
    analytics = svc.get_analytics()
    assert analytics.delivery_success_rate > 0.90
    assert analytics.mean_time_to_acknowledge_seconds > 0
