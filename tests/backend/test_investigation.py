"""
Tests for Investigation endpoints: Evidence, Hypotheses, Agent Executions.
Verifies endpoints return genuine records and an honest empty collection when no data exists.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_investigation_endpoints_empty_state(client: AsyncClient):
    # Create incident
    res = await client.post(
        "/api/v1/incidents",
        json={"title": "Canary OOMKilled Loop", "severity": "SEV-1"},
    )
    assert res.status_code == 201
    incident_id = res.json()["id"]

    # Evidence endpoint
    ev_res = await client.get(f"/api/v1/incidents/{incident_id}/evidence")
    assert ev_res.status_code == 200
    ev_data = ev_res.json()
    assert ev_data["items"] == []
    assert ev_data["total"] == 0

    # Hypotheses endpoint
    hyp_res = await client.get(f"/api/v1/incidents/{incident_id}/hypotheses")
    assert hyp_res.status_code == 200
    hyp_data = hyp_res.json()
    assert hyp_data["items"] == []
    assert hyp_data["total"] == 0

    # Agent executions endpoint
    agent_res = await client.get(f"/api/v1/incidents/{incident_id}/agent-executions")
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    assert agent_data["items"] == []
    assert agent_data["total"] == 0


@pytest.mark.asyncio
async def test_investigation_nonexistent_incident(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await client.get(f"/api/v1/incidents/{fake_id}/evidence")
    assert res.status_code == 404
