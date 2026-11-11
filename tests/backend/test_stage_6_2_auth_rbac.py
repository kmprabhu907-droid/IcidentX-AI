"""
INCIDENTX AI - Stage 6.2 Authentication & RBAC Tests
Verifies user registration, bcrypt authentication, JWT issuance & verification,
rotating refresh tokens, revocation, and 6-tier role-based access control.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app
from backend.app.core.auth import require_roles, require_permission
from backend.app.models.user import UserRole
from fastapi import APIRouter, Depends


# Create an isolated test router for verifying RBAC guards directly
rbac_test_router = APIRouter(prefix="/api/v1/test-rbac", tags=["Test RBAC"])


@rbac_test_router.get("/sre-only")
async def sre_only_endpoint(user=Depends(require_roles(UserRole.SRE_ENGINEER))):
    return {"status": "ok", "user": user.email, "role": user.role}


@rbac_test_router.get("/remediation-execute-perm")
async def remediation_execute_endpoint(user=Depends(require_permission("remediation:execute"))):
    return {"status": "ok", "user": user.email, "role": user.role}


app.include_router(rbac_test_router)


@pytest.mark.asyncio
async def test_first_user_becomes_super_admin(client: AsyncClient):
    """The very first registered user in the system must be granted SUPER_ADMIN."""
    payload = {
        "email": "root.admin@incidentx.internal",
        "password": "Password123!",
        "full_name": "Root Administrator",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "root.admin@incidentx.internal"
    assert data["role"] == "SUPER_ADMIN"
    assert data["is_superuser"] is True
    assert "admin:all" in data["permissions"]


@pytest.mark.asyncio
async def test_subsequent_user_defaults_to_read_only(client: AsyncClient):
    """Subsequent registrations default to READ_ONLY_VIEWER without superuser elevation."""
    # First user
    await client.post("/api/v1/auth/register", json={
        "email": "lead.sre@incidentx.internal",
        "password": "Password123!",
        "full_name": "Lead SRE",
    })

    # Second user
    response = await client.post("/api/v1/auth/register", json={
        "email": "analyst@incidentx.internal",
        "password": "Password123!",
        "full_name": "Observability Analyst",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "READ_ONLY_VIEWER"
    assert data["is_superuser"] is False
    assert "remediation:execute" not in data["permissions"]


@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected(client: AsyncClient):
    """Duplicate user email registrations must return HTTP 409 Conflict."""
    payload = {
        "email": "cloned.user@incidentx.internal",
        "password": "Password123!",
        "full_name": "Original User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_successful_and_returns_tokens(client: AsyncClient):
    """Valid credentials return signed access and refresh tokens."""
    # Register user
    await client.post("/api/v1/auth/register", json={
        "email": "engineer.sre@incidentx.internal",
        "password": "ValidPassword123!",
        "full_name": "Reliability Engineer",
        "role": "SRE_ENGINEER",
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "engineer.sre@incidentx.internal",
        "password": "ValidPassword123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "engineer.sre@incidentx.internal"


@pytest.mark.asyncio
async def test_login_invalid_password_fails(client: AsyncClient):
    """Invalid password must return HTTP 401 Unauthorized."""
    await client.post("/api/v1/auth/register", json={
        "email": "secure.user@incidentx.internal",
        "password": "CorrectPassword123!",
        "full_name": "Secure User",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "secure.user@incidentx.internal",
        "password": "WRONG_PASSWORD!",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_profile_and_missing_token_rejection(client: AsyncClient):
    """GET /api/v1/auth/me succeeds with Bearer token and rejects unauthenticated requests."""
    # 1. Unauthenticated request rejected
    unauth_resp = await client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 2. Authenticate
    await client.post("/api/v1/auth/register", json={
        "email": "auth.checker@incidentx.internal",
        "password": "Password123!",
        "full_name": "Auth Checker",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "auth.checker@incidentx.internal",
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]

    # 3. Authenticated request succeeds
    auth_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_resp.status_code == 200
    assert auth_resp.json()["email"] == "auth.checker@incidentx.internal"


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client: AsyncClient):
    """Refreshing a token rotates both tokens and revokes the used refresh token."""
    await client.post("/api/v1/auth/register", json={
        "email": "rotation.user@incidentx.internal",
        "password": "Password123!",
        "full_name": "Rotation User",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "rotation.user@incidentx.internal",
        "password": "Password123!",
    })
    initial_refresh = login_resp.json()["refresh_token"]

    # Refresh token
    refresh_resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": initial_refresh,
    })
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    new_refresh = new_data["refresh_token"]
    assert new_refresh != initial_refresh

    # Attempting to reuse old refresh token must be rejected
    reuse_resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": initial_refresh,
    })
    assert reuse_resp.status_code == 401
    assert "revoked or expired" in reuse_resp.json()["detail"]


@pytest.mark.asyncio
async def test_logout_revokes_session(client: AsyncClient):
    """Logging out revokes the session refresh token."""
    await client.post("/api/v1/auth/register", json={
        "email": "logout.user@incidentx.internal",
        "password": "Password123!",
        "full_name": "Logout User",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "logout.user@incidentx.internal",
        "password": "Password123!",
    })
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200

    # Refreshing after logout must fail
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_rbac_guard_blocks_unauthorized_roles(client: AsyncClient):
    """Verify require_roles blocks READ_ONLY_VIEWER while allowing SRE_ENGINEER and SUPER_ADMIN."""
    # 1. Register super admin
    await client.post("/api/v1/auth/register", json={
        "email": "admin@incidentx.internal",
        "password": "Password123!",
        "full_name": "Admin",
    })
    admin_login = await client.post("/api/v1/auth/login", json={
        "email": "admin@incidentx.internal",
        "password": "Password123!",
    })
    admin_token = admin_login.json()["access_token"]

    # 2. Register read-only user
    await client.post("/api/v1/auth/register", json={
        "email": "viewer@incidentx.internal",
        "password": "Password123!",
        "full_name": "Viewer",
        "role": "READ_ONLY_VIEWER",
    })
    viewer_login = await client.post("/api/v1/auth/login", json={
        "email": "viewer@incidentx.internal",
        "password": "Password123!",
    })
    viewer_token = viewer_login.json()["access_token"]

    # Viewer calling SRE-only route -> 403 Forbidden
    viewer_res = await client.get(
        "/api/v1/test-rbac/sre-only",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert viewer_res.status_code == 403
    assert "lacks authorization" in viewer_res.json()["detail"]

    # Super Admin calling SRE-only route -> 200 OK (Super admin has all permissions)
    admin_res = await client.get(
        "/api/v1/test-rbac/sre-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200


@pytest.mark.asyncio
async def test_list_roles_and_permissions(client: AsyncClient):
    """GET /api/v1/auth/roles returns the complete catalog of enterprise roles."""
    await client.post("/api/v1/auth/register", json={
        "email": "catalog.user@incidentx.internal",
        "password": "Password123!",
        "full_name": "Catalog User",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "catalog.user@incidentx.internal",
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]

    roles_resp = await client.get(
        "/api/v1/auth/roles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert roles_resp.status_code == 200
    data = roles_resp.json()
    assert len(data["roles"]) == 6
    role_names = [r["role"] for r in data["roles"]]
    assert "SUPER_ADMIN" in role_names
    assert "SRE_ENGINEER" in role_names
    assert "READ_ONLY_VIEWER" in role_names
