"""
Tests for Incident creation, retrieval, validation, and listing.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_incident_success(client: AsyncClient):
    payload = {
        "title": "Database connection pool exhaustion in checkout service",
        "summary": "PostgreSQL pool saturated with unclosed transactions.",
        "severity": "SEV-1",
        "status": "DETECTED",
        "impact_scope": "checkout-service, api-gateway",
    }
    response = await client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["severity"] == "SEV-1"
    assert data["status"] == "DETECTED"
    assert "id" in data
    assert "detected_at" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_incident_invalid_severity(client: AsyncClient):
    payload = {
        "title": "Invalid Severity Test",
        "severity": "SEV-99",  # Invalid
    }
    response = await client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RequestValidationError"


@pytest.mark.asyncio
async def test_create_incident_title_too_short(client: AsyncClient):
    payload = {
        "title": "ab",  # min_length is 3
        "severity": "SEV-2",
    }
    response = await client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_incident_by_id(client: AsyncClient):
    # Create incident
    create_res = await client.post(
        "/api/v1/incidents",
        json={"title": "Redis Cache Invalidation Storm", "severity": "SEV-2"},
    )
    assert create_res.status_code == 201
    incident_id = create_res.json()["id"]

    # Retrieve incident
    get_res = await client.get(f"/api/v1/incidents/{incident_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == incident_id
    assert data["title"] == "Redis Cache Invalidation Storm"


@pytest.mark.asyncio
async def test_get_incident_not_found(client: AsyncClient):
    response = await client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "EntityNotFoundException"


@pytest.mark.asyncio
async def test_list_incidents_pagination(client: AsyncClient):
    for i in range(5):
        await client.post(
            "/api/v1/incidents",
            json={"title": f"Test Incident #{i}", "severity": "SEV-3"},
        )

    res = await client.get("/api/v1/incidents?page=1&page_size=3")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["page_size"] == 3
