"""
INCIDENTX AI - Stage 6.5 Event-Driven Architecture & Workflow Engine Tests
Verifies asynchronous EventBus Pub/Sub, multi-step reliability state machine,
human-in-the-loop approval pause/resume, and rejection handling.
"""

import pytest
from httpx import AsyncClient
from backend.app.services.events.bus import event_bus
from backend.app.services.events.events import (
    DomainEvent,
    IncidentDetectedEvent,
    RemediationExecutedEvent,
)


@pytest.fixture(autouse=True)
async def cleanup_event_bus():
    """Ensure clean event bus state before and after each test."""
    await event_bus.clear()
    yield
    await event_bus.clear()


async def _register_and_login(client: AsyncClient, email: str, name: str, role: str = "SRE_ENGINEER") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": name,
        "role": role,
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Password123!",
    })
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_event_bus_pub_sub_and_wildcard():
    """Verify EventBus dispatches to specific subscribers and wildcard '*' listeners."""
    received_specific = []
    received_wildcard = []

    async def specific_handler(event: DomainEvent):
        received_specific.append(event)

    async def wildcard_handler(event: DomainEvent):
        received_wildcard.append(event)

    await event_bus.subscribe("ai.incidentx.incident.detected", specific_handler)
    await event_bus.subscribe("*", wildcard_handler)

    test_event = IncidentDetectedEvent(
        organization_id="org-test",
        data={"incident_id": "inc-001", "service": "payment-service"},
    )
    await event_bus.publish(test_event)

    assert len(received_specific) == 1
    assert received_specific[0].data["service"] == "payment-service"
    assert len(received_wildcard) == 1
    assert received_wildcard[0].id == test_event.id

    # Unsubscribe specific handler
    await event_bus.unsubscribe("ai.incidentx.incident.detected", specific_handler)
    second_event = IncidentDetectedEvent(
        organization_id="org-test",
        data={"incident_id": "inc-002", "service": "order-service"},
    )
    await event_bus.publish(second_event)

    assert len(received_specific) == 1  # Unsubscribed, count unchanged
    assert len(received_wildcard) == 2  # Wildcard still active


@pytest.mark.asyncio
async def test_workflow_auto_approve_lifecycle(client: AsyncClient):
    """Triggering a workflow with auto_approve=True runs through to COMPLETED status."""
    token = await _register_and_login(client, "sre.auto@incidentx.internal", "Auto SRE")

    response = await client.post(
        "/api/v1/workflows/trigger",
        json={
            "service_name": "checkout-service",
            "severity": "SEV-1",
            "title": "Cascading Database Deadlock",
            "auto_approve": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["current_step"] == "COMPLETED"

    # Verify all 6 sequential step records exist
    step_names = [s["step"] for s in data["step_history"]]
    assert "DETECTION" in step_names
    assert "INVESTIGATION" in step_names
    assert "PLANNING" in step_names
    assert "REMEDIATION" in step_names
    assert "VERIFICATION" in step_names
    assert "COMPLETED" in step_names


@pytest.mark.asyncio
async def test_workflow_human_approval_pause_and_resume(client: AsyncClient):
    """Workflow with auto_approve=False pauses at AWAITING_APPROVAL and resumes on approval."""
    token = await _register_and_login(client, "sre.human@incidentx.internal", "Human SRE", role="SRE_ENGINEER")

    # 1. Trigger workflow (pauses at approval gateway)
    trigger_res = await client.post(
        "/api/v1/workflows/trigger",
        json={
            "service_name": "inventory-service",
            "severity": "SEV-2",
            "title": "Memory Leak Anomaly Detected",
            "auto_approve": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert trigger_res.status_code == 201
    data = trigger_res.json()
    wf_id = data["id"]
    assert data["status"] == "AWAITING_APPROVAL"
    assert data["current_step"] == "APPROVAL_GATEWAY"

    # 2. Inspect workflow state
    get_res = await client.get(f"/api/v1/workflows/{wf_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "AWAITING_APPROVAL"

    # 3. Resume workflow with approval
    resume_res = await client.post(
        f"/api/v1/workflows/{wf_id}/resume",
        json={"approved": True, "comment": "Verified blast radius. Approved for rolling restart."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resume_res.status_code == 200
    resumed_data = resume_res.json()
    assert resumed_data["status"] == "COMPLETED"
    assert resumed_data["current_step"] == "COMPLETED"

    step_statuses = {s["step"]: s["status"] for s in resumed_data["step_history"]}
    assert step_statuses.get("REMEDIATION") == "COMPLETED"
    assert step_statuses.get("VERIFICATION") == "COMPLETED"


@pytest.mark.asyncio
async def test_workflow_human_rejection(client: AsyncClient):
    """Rejecting a paused workflow transitions it to FAILED status."""
    token = await _register_and_login(client, "sre.reject@incidentx.internal", "Reject SRE")

    trigger_res = await client.post(
        "/api/v1/workflows/trigger",
        json={"service_name": "auth-service", "severity": "SEV-2", "auto_approve": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = trigger_res.json()["id"]

    # Reject
    resume_res = await client.post(
        f"/api/v1/workflows/{wf_id}/resume",
        json={"approved": False, "comment": "High risk during peak traffic window. Rejected."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resume_res.status_code == 200
    rejected_data = resume_res.json()
    assert rejected_data["status"] == "FAILED"


@pytest.mark.asyncio
async def test_workflow_tenant_isolation(client: AsyncClient):
    """Workflows triggered in Tenant Alpha cannot be accessed or listed by Tenant Beta."""
    token_a = await _register_and_login(client, "alpha.wf@alpha.internal", "Alpha SRE")
    token_b = await _register_and_login(client, "beta.wf@beta.internal", "Beta SRE")

    # Create Org Alpha and Org Beta
    await client.post("/api/v1/organizations", json={"name": "Org Alpha WF", "slug": "org-alpha-wf"}, headers={"Authorization": f"Bearer {token_a}"})
    await client.post("/api/v1/organizations", json={"name": "Org Beta WF", "slug": "org-beta-wf"}, headers={"Authorization": f"Bearer {token_b}"})

    # Trigger workflow under Org Alpha
    wf_res = await client.post(
        "/api/v1/workflows/trigger",
        json={"service_name": "alpha-service", "auto_approve": True},
        headers={"Authorization": f"Bearer {token_a}", "X-Organization-ID": "org-alpha-wf"},
    )
    assert wf_res.status_code == 201

    # Alpha SRE lists workflows under Org Alpha -> sees 1 workflow
    list_a = await client.get("/api/v1/workflows", headers={"Authorization": f"Bearer {token_a}", "X-Organization-ID": "org-alpha-wf"})
    assert len(list_a.json()) == 1

    # Beta SRE lists workflows under Org Beta -> sees 0 workflows
    list_b = await client.get("/api/v1/workflows", headers={"Authorization": f"Bearer {token_b}", "X-Organization-ID": "org-beta-wf"})
    assert len(list_b.json()) == 0
