"""
INCIDENTX AI - Authentication & RBAC API Router (Stage 6.2)
Provides enterprise identity endpoints: registration, authentication, token refresh, logout, and self-inspection.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, require_roles
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.app.models.user import ROLE_PERMISSIONS, RefreshToken, User, UserRole
from backend.app.schemas.auth import (
    MessageResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


def _hash_token(token_str: str) -> str:
    """Hashes a refresh token string for safe database persistence."""
    return hashlib.sha256(token_str.encode("utf-8")).hexdigest()


def _build_user_response(user: User) -> UserResponse:
    """Constructs UserResponse with resolved permissions."""
    role_enum = None
    try:
        role_enum = UserRole(user.role)
    except ValueError:
        pass

    permissions = list(ROLE_PERMISSIONS.get(role_enum, set())) if role_enum else []
    if user.is_superuser:
        permissions.append("admin:all")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        organization_id=user.organization_id,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        permissions=sorted(permissions),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check if email is already registered
    existing_stmt = select(User).where(User.email == payload.email.lower().strip())
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists.",
        )

    # Check user count: bootstrap the very first registered user as SUPER_ADMIN
    count_stmt = select(func.count(User.id))
    total_users = (await db.execute(count_stmt)).scalar() or 0

    assigned_role = payload.role.value if payload.role else UserRole.READ_ONLY_VIEWER.value
    is_superuser = False

    if total_users == 0:
        assigned_role = UserRole.SUPER_ADMIN.value
        is_superuser = True

    new_user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=assigned_role,
        is_active=True,
        is_superuser=is_superuser,
        organization_id=payload.organization_id,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return _build_user_response(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
)
async def login(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == payload.email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact your organization administrator.",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)

    # Issue access and refresh tokens
    token_claims = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "org_id": user.organization_id,
    }
    access_token = create_access_token(token_claims)
    refresh_token = create_refresh_token(token_claims)

    # Persist hashed refresh token for revocation and rotation tracking
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(refresh_record)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=_build_user_response(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue fresh access token",
)
async def refresh_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided token is not a valid refresh token.",
            )
        user_id = decoded.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired, invalid, or malformed.",
        )

    # Check persistence and revocation
    hashed = _hash_token(payload.refresh_token)
    token_stmt = select(RefreshToken).where(
        RefreshToken.token_hash == hashed,
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    )
    token_result = await db.execute(token_stmt)
    token_record = token_result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired.",
        )

    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired.",
        )

    # Revoke used refresh token (rotation policy)
    token_record.revoked = True

    # Retrieve user
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists.",
        )

    # Issue new token pair
    token_claims = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "org_id": user.organization_id,
    }
    new_access_token = create_access_token(token_claims)
    new_refresh_token = create_refresh_token(token_claims)

    new_refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(new_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(new_refresh_record)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=_build_user_response(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke active refresh token",
)
async def logout(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    hashed = _hash_token(payload.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hashed)
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()

    if token_record:
        token_record.revoked = True
        await db.commit()

    return MessageResponse(message="Session successfully terminated and refresh token revoked.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Inspect current authenticated user and permissions",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return _build_user_response(current_user)


@router.get(
    "/roles",
    summary="List available enterprise RBAC roles and permissions",
)
async def list_roles(
    current_user: User = Depends(get_current_user),
):
    return {
        "roles": [
            {
                "role": role.value,
                "permissions": sorted(list(perms)),
            }
            for role, perms in ROLE_PERMISSIONS.items()
        ]
    }
