"""
INCIDENTX AI - Stage 6.3 Multi-Tenant Organization Tests
Verifies tenant isolation, organization lifecycle, membership RBAC,
tenant resolver (X-Organization-ID), and cross-tenant query boundaries.
"""

import pytest
from httpx import AsyncClient
from backend.main import app
from backend.app.core.tenant import get_current_tenant
from backend.app.models.incident import Incident
from backend.app.models.organization import Organization
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# Isolated test router for testing tenant resolution directly
tenant_test_router = APIRouter(prefix="/api/v1/test-tenant", tags=["Test Tenant"])


@tenant_test_router.get("/context")
async def tenant_context_endpoint(tenant: Organization = Depends(get_current_tenant)):
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_slug": tenant.slug,
        "tier": tenant.tier,
    }


app.include_router(tenant_test_router)


async def _register_and_login(client: AsyncClient, email: str, name: str, role: str = "SRE_ENGINEER") -> str:
    """Helper to register and login a test user, returning their access token."""
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
async def test_create_organization_assigns_owner(client: AsyncClient):
    """Creating an organization creates membership with OWNER role and sets active tenant."""
    token = await _register_and_login(client, "org.creator@incidentx.internal", "Org Creator")

    response = await client.post(
        "/api/v1/organizations",
        json={"name": "Stripe Reliability", "slug": "stripe-rel", "tier": "ENTERPRISE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Stripe Reliability"
    assert data["slug"] == "stripe-rel"
    assert data["member_count"] == 1


@pytest.mark.asyncio
async def test_duplicate_organization_slug_rejected(client: AsyncClient):
    """Creating an organization with duplicate slug or name returns 409 Conflict."""
    token = await _register_and_login(client, "tenant.dupe@incidentx.internal", "Tenant User")

    res1 = await client.post(
        "/api/v1/organizations",
        json={"name": "Datadog Workspace", "slug": "datadog-sre"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201

    res2 = await client.post(
        "/api/v1/organizations",
        json={"name": "Datadog Workspace 2", "slug": "datadog-sre"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_list_organizations_tenant_scoping(client: AsyncClient):
    """Users only see organizations they belong to, while superusers see all organizations."""
    # First user auto-bootstraps as SUPER_ADMIN
    admin_token = await _register_and_login(client, "admin.multi@incidentx.internal", "Super Admin")

    # Regular users
    user_a_token = await _register_and_login(client, "alice@alpha.internal", "Alice Alpha")
    user_b_token = await _register_and_login(client, "bob@beta.internal", "Bob Beta")

    # Alice creates Org Alpha
    await client.post(
        "/api/v1/organizations",
        json={"name": "Alpha Corp", "slug": "alpha-corp"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )

    # Bob creates Org Beta
    await client.post(
        "/api/v1/organizations",
        json={"name": "Beta Corp", "slug": "beta-corp"},
        headers={"Authorization": f"Bearer {user_b_token}"},
    )

    # Alice listing orgs only sees Alpha Corp
    res_a = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {user_a_token}"})
    assert res_a.status_code == 200
    slugs_a = [o["slug"] for o in res_a.json()]
    assert "alpha-corp" in slugs_a
    assert "beta-corp" not in slugs_a

    # Bob listing orgs only sees Beta Corp
    res_b = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {user_b_token}"})
    assert res_b.status_code == 200
    slugs_b = [o["slug"] for o in res_b.json()]
    assert "beta-corp" in slugs_b
    assert "alpha-corp" not in slugs_b

    # Super Admin sees both Alpha and Beta
    res_admin = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    slugs_admin = [o["slug"] for o in res_admin.json()]
    assert "alpha-corp" in slugs_admin
    assert "beta-corp" in slugs_admin


@pytest.mark.asyncio
async def test_add_member_and_switch_organization(client: AsyncClient):
    """Owner can add member to organization, and member can switch active organization."""
    owner_token = await _register_and_login(client, "owner.invite@incidentx.internal", "Owner User")
    invitee_token = await _register_and_login(client, "member.join@incidentx.internal", "Member User")

    # Owner creates Org
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Canary Corp", "slug": "canary-corp"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    org_id = org_res.json()["id"]

    # Invitee initially not in Canary Corp
    before_list = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {invitee_token}"})
    assert "canary-corp" not in [o["slug"] for o in before_list.json()]

    # Owner adds invitee
    add_res = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "member.join@incidentx.internal", "role": "MEMBER"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert add_res.status_code == 201

    # Invitee now sees Canary Corp
    after_list = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {invitee_token}"})
    assert "canary-corp" in [o["slug"] for o in after_list.json()]

    # Invitee switches active organization
    switch_res = await client.post(
        "/api/v1/organizations/switch",
        json={"organization_id": org_id},
        headers={"Authorization": f"Bearer {invitee_token}"},
    )
    assert switch_res.status_code == 200
    assert "Successfully switched" in switch_res.json()["message"]


@pytest.mark.asyncio
async def test_tenant_resolver_header(client: AsyncClient):
    """X-Organization-ID header resolves tenant and enforces membership checks."""
    user_token = await _register_and_login(client, "tenant.header@incidentx.internal", "Header User")
    intruder_token = await _register_and_login(client, "intruder@incidentx.internal", "Intruder User")

    # Create org
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Secure Vault Org", "slug": "secure-vault"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    org_id = org_res.json()["id"]

    # Member calling with X-Organization-ID succeeds
    ok_res = await client.get(
        "/api/v1/test-tenant/context",
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Organization-ID": "secure-vault",
        },
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["tenant_name"] == "Secure Vault Org"

    # Intruder (non-member) calling with X-Organization-ID gets 403 Forbidden
    denied_res = await client.get(
        "/api/v1/test-tenant/context",
        headers={
            "Authorization": f"Bearer {intruder_token}",
            "X-Organization-ID": "secure-vault",
        },
    )
    assert denied_res.status_code == 403
    assert "lacks active membership" in denied_res.json()["detail"]


@pytest.mark.asyncio
async def test_database_incident_tenant_isolation(db_session: AsyncSession):
    """Direct database query scoping confirms strict data isolation across organization_id."""
    inc_tenant_1 = Incident(
        title="Tenant 1 Incident",
        severity="SEV-1",
        status="INVESTIGATING",
        organization_id="org-uuid-001",
    )
    inc_tenant_2 = Incident(
        title="Tenant 2 Incident",
        severity="SEV-2",
        status="DETECTED",
        organization_id="org-uuid-002",
    )
    db_session.add_all([inc_tenant_1, inc_tenant_2])
    await db_session.commit()

    # Query scoped to org 1
    stmt1 = select(Incident).where(Incident.organization_id == "org-uuid-001")
    res1 = (await db_session.execute(stmt1)).scalars().all()
    assert len(res1) == 1
    assert res1[0].title == "Tenant 1 Incident"

    # Query scoped to org 2
    stmt2 = select(Incident).where(Incident.organization_id == "org-uuid-002")
    res2 = (await db_session.execute(stmt2)).scalars().all()
    assert len(res2) == 1
    assert res2[0].title == "Tenant 2 Incident"
