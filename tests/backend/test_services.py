"""
Tests for Services, Dependencies, and database constraints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_service_success(client: AsyncClient):
    payload = {
        "name": "payment-service",
        "tier": "Tier-1",
        "service_type": "service",
        "language": "Go",
        "health_status": "HEALTHY",
    }
    response = await client.post("/api/v1/services", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "payment-service"
    assert data["tier"] == "Tier-1"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_service_duplicate_name_constraint(client: AsyncClient):
    payload = {"name": "auth-service", "tier": "Tier-1", "service_type": "service"}
    res1 = await client.post("/api/v1/services", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate creation
    res2 = await client.post("/api/v1/services", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error"]["code"] == "EntityConflictException"


@pytest.mark.asyncio
async def test_create_dependency_success(client: AsyncClient):
    # Create two services
    s1 = await client.post("/api/v1/services", json={"name": "api-gateway", "tier": "Tier-1", "service_type": "gateway"})
    s2 = await client.post("/api/v1/services", json={"name": "order-service", "tier": "Tier-1", "service_type": "service"})
    assert s1.status_code == 201
    assert s2.status_code == 201

    id1 = s1.json()["id"]
    id2 = s2.json()["id"]

    dep_res = await client.post(
        "/api/v1/dependencies",
        json={
            "source_service_id": id1,
            "target_service_id": id2,
            "protocol": "gRPC",
            "is_critical": True,
        },
    )
    assert dep_res.status_code == 201
    dep_data = dep_res.json()
    assert dep_data["source_service_id"] == id1
    assert dep_data["target_service_id"] == id2
    assert dep_data["protocol"] == "gRPC"


@pytest.mark.asyncio
async def test_create_dependency_self_loop_rejected(client: AsyncClient):
    s1 = await client.post("/api/v1/services", json={"name": "standalone-worker", "tier": "Tier-2"})
    assert s1.status_code == 201
    svc_id = s1.json()["id"]

    dep_res = await client.post(
        "/api/v1/dependencies",
        json={"source_service_id": svc_id, "target_service_id": svc_id, "protocol": "HTTP"},
    )
    assert dep_res.status_code == 409


@pytest.mark.asyncio
async def test_create_dependency_nonexistent_service(client: AsyncClient):
    dep_res = await client.post(
        "/api/v1/dependencies",
        json={
            "source_service_id": "00000000-0000-0000-0000-000000000001",
            "target_service_id": "00000000-0000-0000-0000-000000000002",
        },
    )
    assert dep_res.status_code == 404
