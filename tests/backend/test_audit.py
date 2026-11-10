"""
Tests for Audit Log generation and inspection.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_log_created_on_incident(client: AsyncClient):
    # Create incident
    res = await client.post(
        "/api/v1/incidents",
        json={"title": "Audited Test Incident", "severity": "SEV-2"},
    )
    assert res.status_code == 201
    incident_id = res.json()["id"]

    # Verify audit log was created
    audit_res = await client.get("/api/v1/audit-logs")
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert data["total"] >= 1

    # Check for matching incident audit log
    matching = [log for log in data["items"] if log["incident_id"] == incident_id]
    assert len(matching) == 1
    assert matching[0]["action"] == "INCIDENT_CREATED"
    assert matching[0]["actor_type"] == "USER"
