"""
INCIDENTX AI - Phase 9 Intelligent On-Call Incident Command Center Test Suite
Tests Modules 9.1 through 9.5:
- Module 9.1: Central Incident Lifecycle Engine & Transition State Machine
- Module 9.2: Live Incident Timeline Engine & SSE Broadcasting
- Module 9.3: Intelligent Alert Ingestion Engine (Alertmanager, Grafana, K8s, Webhook) & Deduplication
- Module 9.4: Incident Ownership & Escalation Engine with SLA Tracking
- Module 9.5: Real-Time Command Center Statistics & Dashboard APIs
"""

import asyncio
from datetime import datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.incident import Incident
from backend.app.models.alert import Alert
from backend.app.services.incident.lifecycle_engine import (
    IncidentLifecycleEngine,
    InvalidLifecycleTransitionException,
)
from backend.app.services.incident.timeline_engine import incident_timeline_engine, timeline_broadcaster
from backend.app.services.incident.alert_ingestion_engine import alert_ingestion_engine
from backend.app.services.incident.ownership_engine import incident_ownership_engine


@pytest.mark.asyncio
async def test_module_9_1_lifecycle_valid_transitions(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies valid lifecycle progression across all standard states:
    DETECTED -> ACKNOWLEDGED -> INVESTIGATING -> ROOT_CAUSE_IDENTIFIED ->
    REMEDIATION_PENDING -> REMEDIATING -> VERIFYING -> RESOLVED -> CLOSED.
    """
    # 1. Create incident in DETECTED state
    create_res = await client.post(
        "/api/v1/incidents",
        json={
            "title": "Payment gateway timeout spike",
            "summary": "Gateway 504 gateway timeout rate exceeds 25%.",
            "severity": "P1",
            "status": "DETECTED",
            "impact_scope": "payment-gateway",
            "environment": "DEMOMESH",
        },
    )
    assert create_res.status_code == 201
    inc_data = create_res.json()
    inc_id = inc_data["id"]
    assert inc_data["status"] == "DETECTED"

    # 2. Transition: DETECTED -> ACKNOWLEDGED
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "ACKNOWLEDGED", "actor": "sre-alice", "actor_type": "HUMAN"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ACKNOWLEDGED"
    assert res.json()["acknowledged_at"] is not None
    assert res.json()["acknowledged_by"] == "sre-alice"

    # 3. Transition: ACKNOWLEDGED -> INVESTIGATING
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "INVESTIGATING", "actor": "InvestigationAgent", "actor_type": "AI_AGENT"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "INVESTIGATING"

    # 4. Transition: INVESTIGATING -> ROOT_CAUSE_IDENTIFIED
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "ROOT_CAUSE_IDENTIFIED", "actor": "RootCauseAgent", "actor_type": "AI_AGENT"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ROOT_CAUSE_IDENTIFIED"

    # 5. Transition: ROOT_CAUSE_IDENTIFIED -> REMEDIATION_PENDING
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "REMEDIATION_PENDING", "actor": "RemediationAgent", "actor_type": "AI_AGENT"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REMEDIATION_PENDING"

    # 6. Transition: REMEDIATION_PENDING -> REMEDIATING
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "REMEDIATING", "actor": "sre-bob", "actor_type": "HUMAN", "reason": "Approved scale out"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REMEDIATING"

    # 7. Transition: REMEDIATING -> VERIFYING
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "VERIFYING", "actor": "VerificationAgent", "actor_type": "AI_AGENT"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "VERIFYING"

    # 8. Transition: VERIFYING -> RESOLVED
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "RESOLVED", "actor": "sre-alice", "actor_type": "HUMAN"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESOLVED"
    assert data["resolved_at"] is not None
    assert data["mttr_seconds"] is not None
    assert data["mttr_seconds"] >= 0

    # 9. Transition: RESOLVED -> CLOSED
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "CLOSED", "actor": "sre-lead", "actor_type": "HUMAN"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"
    assert res.json()["closed_at"] is not None


@pytest.mark.asyncio
async def test_module_9_1_invalid_transition_rejected(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that illegal jumps (e.g. DETECTED -> RESOLVED) are strictly blocked with 400.
    """
    create_res = await client.post(
        "/api/v1/incidents",
        json={"title": "Redis Cache OOM", "severity": "P2", "status": "DETECTED"},
    )
    inc_id = create_res.json()["id"]

    # Try invalid jump: DETECTED directly to RESOLVED
    res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "RESOLVED", "actor": "user-bad"},
    )
    assert res.status_code == 400
    error_msg = res.json().get("error", {}).get("message", "") or res.json().get("detail", "")
    assert "Invalid incident lifecycle transition" in error_msg


@pytest.mark.asyncio
async def test_module_9_1_reopen_cycle(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies RESOLVED -> REOPENED -> INVESTIGATING cycle.
    """
    create_res = await client.post(
        "/api/v1/incidents",
        json={"title": "Memory leak recurrence", "severity": "P2", "status": "DETECTED"},
    )
    inc_id = create_res.json()["id"]

    # Advance to ACKNOWLEDGED then RESOLVED
    await client.post(f"/api/v1/incidents/{inc_id}/transition", json={"target_state": "ACKNOWLEDGED"})
    await client.post(f"/api/v1/incidents/{inc_id}/transition", json={"target_state": "RESOLVED"})

    # Reopen
    reopen_res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "REOPENED", "reason": "Anomaly returned 10m later"},
    )
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "REOPENED"
    assert reopen_res.json()["resolved_at"] is None

    # Advance back to INVESTIGATING
    inv_res = await client.post(
        f"/api/v1/incidents/{inc_id}/transition",
        json={"target_state": "INVESTIGATING"},
    )
    assert inv_res.status_code == 200
    assert inv_res.json()["status"] == "INVESTIGATING"


@pytest.mark.asyncio
async def test_module_9_2_timeline_recording_and_listing(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies chronological timeline event generation with actor and actor_type tags.
    """
    create_res = await client.post(
        "/api/v1/incidents",
        json={"title": "Cart service cascade failure", "severity": "P1", "status": "DETECTED"},
    )
    inc_id = create_res.json()["id"]

    # Add custom timeline events via engine
    await incident_timeline_engine.record_event(
        incident_id=inc_id,
        event_type="METRIC_ANOMALY",
        service_name="cart-service",
        title="P99 Latency 4200ms Spike",
        description="Observed 12x baseline latency surge over 60s.",
        severity="CRITICAL",
        actor="TelemetryAnalysisAgent",
        actor_type="AI_AGENT",
        session=db_session,
    )

    await incident_timeline_engine.record_event(
        incident_id=inc_id,
        event_type="OPERATOR_NOTE",
        service_name="cart-service",
        title="Shift Handover Note",
        description="Scaling deployment to 8 replicas to shed queue load.",
        severity="INFO",
        actor="sre-charlie@enterprise.io",
        actor_type="HUMAN",
        session=db_session,
    )

    # Fetch timeline via API
    res = await client.get(f"/api/v1/incidents/{inc_id}/timeline")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 2

    # Check actor types
    actor_types = {e["actor_type"] for e in events}
    assert "AI_AGENT" in actor_types
    assert "HUMAN" in actor_types


@pytest.mark.asyncio
async def test_module_9_2_timeline_broadcaster_pubsub():
    """
    Verifies that the in-memory SSE timeline broadcaster broadcasts events to active subscriber queues.
    """
    test_inc_id = f"test-inc-{uuid.uuid4().hex[:8]}"
    q = await timeline_broadcaster.subscribe(test_inc_id)

    event_payload = {
        "incident_id": test_inc_id,
        "title": "Database Master Failover Completed",
        "actor": "KubernetesInvestigatorAgent",
        "actor_type": "AI_AGENT",
    }
    await timeline_broadcaster.broadcast(test_inc_id, event_payload)

    received = await asyncio.wait_for(q.get(), timeout=2.0)
    assert received["title"] == "Database Master Failover Completed"
    assert received["actor_type"] == "AI_AGENT"

    await timeline_broadcaster.unsubscribe(test_inc_id, q)


@pytest.mark.asyncio
async def test_module_9_3_alert_ingestion_alertmanager(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies Alertmanager webhook ingestion, automatic incident creation, fingerprinting, and sub-second auto-ack.
    """
    alertmanager_payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PodCrashLooping",
                    "service": "billing-service",
                    "severity": "P1",
                    "environment": "DEMOMESH",
                },
                "annotations": {
                    "summary": "Billing service pod restarted 5 times in 10 minutes",
                    "description": "CrashLoopBackOff detected on billing-service-pod-x92",
                },
            }
        ]
    }

    res = await client.post("/api/v1/alerts/ingest", json=alertmanager_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["action"] == "CREATED"
    assert data["is_new_incident"] is True
    assert data["service_name"] == "billing-service"
    assert data["severity"] == "P1"
    assert len(data["fingerprint"]) == 64

    # Verify that the incident was auto-acknowledged
    inc_res = await client.get(f"/api/v1/incidents/{data['incident_id']}")
    assert inc_res.status_code == 200
    incident = inc_res.json()
    assert incident["status"] == "ACKNOWLEDGED"
    assert incident["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_module_9_3_alert_deduplication_and_correlation(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that a subsequent alert with the same fingerprint correlates to the existing incident
    instead of spamming duplicate incidents.
    """
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighMemoryUtilization",
                    "service": "order-service",
                    "severity": "P2",
                    "environment": "DEMOMESH",
                },
                "annotations": {
                    "summary": "Order service container memory > 90%",
                },
            }
        ]
    }

    # First ingest -> CREATED
    res1 = await client.post("/api/v1/alerts/ingest", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["action"] == "CREATED"
    first_inc_id = data1["incident_id"]

    # Second ingest -> CORRELATED (same fingerprint)
    res2 = await client.post("/api/v1/alerts/ingest", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["action"] == "CORRELATED"
    assert data2["is_new_incident"] is False
    assert data2["incident_id"] == first_inc_id
    assert "correlated with active incident" in data2["summary"].lower()


@pytest.mark.asyncio
async def test_module_9_3_grafana_and_k8s_alert_normalization(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that Grafana Alerting and Kubernetes Event payloads normalize cleanly.
    """
    # 1. Grafana format
    grafana_payload = {
        "ruleName": "GrafanaPostgresDiskSpaceCritical",
        "tags": {"service": "postgres-db", "severity": "P1"},
        "message": "Disk space left on /var/lib/postgresql is under 3%.",
    }
    g_res = await client.post("/api/v1/alerts/ingest", json=grafana_payload)
    assert g_res.status_code == 201
    assert g_res.json()["action"] == "CREATED"
    assert g_res.json()["service_name"] == "postgres-db"

    # 2. Kubernetes event format
    k8s_payload = {
        "reason": "OOMKilled",
        "message": "Container search-worker exceeded memory limit of 512MiB",
        "involvedObject": {"name": "search-worker", "kind": "Pod"},
        "type": "Warning",
    }
    k_res = await client.post("/api/v1/alerts/ingest", json=k8s_payload)
    assert k_res.status_code == 201
    assert k_res.json()["action"] == "CREATED"
    assert k_res.json()["service_name"] == "search-worker"


@pytest.mark.asyncio
async def test_module_9_4_ownership_assign_reassign_escalate(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies assignment, reassignment with required reason, acknowledgment, and escalation tiers.
    """
    # 1. Create incident
    create_res = await client.post(
        "/api/v1/incidents",
        json={"title": "Authentication token validation failures", "severity": "P1", "status": "DETECTED"},
    )
    inc_id = create_res.json()["id"]

    # 2. Assign owner
    assign_res = await client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={
            "assigned_to_id": "usr-101",
            "assigned_to_name": "Dave Miller",
            "team_name": "Identity SRE",
            "assigned_by": "sre-manager",
            "role": "PRIMARY_RESPONDER",
            "reason": "Token service owner",
        },
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["owner_id"] == "usr-101"
    assert assign_res.json()["owner_name"] == "Dave Miller"
    assert assign_res.json()["assigned_team"] == "Identity SRE"

    # 3. Reassign owner
    reassign_res = await client.post(
        f"/api/v1/incidents/{inc_id}/reassign",
        json={
            "new_owner_id": "usr-202",
            "new_owner_name": "Elena Rostova",
            "new_team_name": "Core Security",
            "assigned_by": "Dave Miller",
            "reason": "Shift handover to EMEA team",
        },
    )
    assert reassign_res.status_code == 200
    assert reassign_res.json()["owner_id"] == "usr-202"
    assert reassign_res.json()["owner_name"] == "Elena Rostova"
    assert reassign_res.json()["assigned_team"] == "Core Security"

    # 4. Acknowledge
    ack_res = await client.post(
        f"/api/v1/incidents/{inc_id}/acknowledge",
        json={"responder_id": "usr-202", "responder_name": "Elena Rostova"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged_by"] == "Elena Rostova"
    assert ack_res.json()["acknowledged_at"] is not None

    # 5. Escalate
    esc_res = await client.post(
        f"/api/v1/incidents/{inc_id}/escalate",
        json={
            "reason": "Multi-region cascade risk identified",
            "target_tier": "ESCALATED_TIER_3",
            "escalated_by": "Elena Rostova",
        },
    )
    assert esc_res.status_code == 200
    assert esc_res.json()["is_escalated"] is True
    assert esc_res.json()["escalation_status"] == "ESCALATED_TIER_3"

    # 6. Fetch ownership summary
    summary_res = await client.get(f"/api/v1/incidents/{inc_id}/ownership")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["owner_name"] == "Elena Rostova"
    assert summary["is_escalated"] is True
    assert len(summary["assignment_history"]) >= 2


@pytest.mark.asyncio
async def test_module_9_5_incident_statistics_summary(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies GET /api/v1/incidents/statistics/summary aggregates counts, P1/P2/P3/P4,
    investigating, unassigned, and MTTA/MTTR properly.
    """
    # Create sample incidents
    await client.post(
        "/api/v1/incidents",
        json={"title": "P1 Active Outage", "severity": "P1", "status": "INVESTIGATING", "environment": "DEMOMESH"},
    )
    await client.post(
        "/api/v1/incidents",
        json={"title": "P2 High Alert", "severity": "P2", "status": "DETECTED", "environment": "KUBERNETES"},
    )

    res = await client.get("/api/v1/incidents/statistics/summary")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_active"] >= 2
    assert stats["p1_critical"] >= 1
    assert stats["p2_high"] >= 1
    assert stats["investigating"] >= 1
    assert "DEMOMESH" in stats["environment_counts"]
    assert "KUBERNETES" in stats["environment_counts"]
