"""
INCIDENTX AI - Organization & Multi-Tenancy API Router (Stage 6.3)
Provides endpoints for tenant lifecycle, member provisioning, RBAC associations, and active workspace switching.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.models.organization import (
    MemberRole,
    Organization,
    OrganizationMembership,
    OrganizationTier,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import MessageResponse, UserResponse
from backend.app.schemas.organization import (
    MemberAddRequest,
    MemberResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    SwitchOrganizationRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations & Multi-Tenancy"])


async def _get_org_member_count(db: AsyncSession, org_id: str) -> int:
    stmt = select(func.count(OrganizationMembership.id)).where(
        OrganizationMembership.organization_id == org_id
    )
    return (await db.execute(stmt)).scalar() or 0


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant organization",
)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if slug or name exists
    existing_stmt = select(Organization).where(
        (Organization.slug == payload.slug.lower().strip()) |
        (Organization.name == payload.name.strip())
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with name '{payload.name}' or slug '{payload.slug}' already exists.",
        )

    tier_value = payload.tier.value if payload.tier else OrganizationTier.ENTERPRISE.value
    new_org = Organization(
        name=payload.name.strip(),
        slug=payload.slug.lower().strip(),
        tier=tier_value,
        settings_json=payload.settings_json or "{}",
        is_active=True,
    )
    db.add(new_org)
    await db.flush()

    # Automatically add creator as OWNER
    membership = OrganizationMembership(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=MemberRole.OWNER.value,
    )
    db.add(membership)

    # Set as active org if user has none
    if not current_user.organization_id:
        current_user.organization_id = new_org.id

    await db.commit()
    await db.refresh(new_org)

    return OrganizationResponse(
        id=new_org.id,
        name=new_org.name,
        slug=new_org.slug,
        tier=new_org.tier,
        is_active=new_org.is_active,
        settings_json=new_org.settings_json,
        created_at=new_org.created_at,
        updated_at=new_org.updated_at,
        member_count=1,
    )


@router.get(
    "",
    response_model=List[OrganizationResponse],
    summary="List organizations accessible to the current user",
)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_superuser:
        # Superuser can inspect all organizations
        stmt = select(Organization).order_by(Organization.name)
        result = await db.execute(stmt)
        orgs = result.scalars().all()
    else:
        # Filter to organizations where user has active membership
        stmt = (
            select(Organization)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(OrganizationMembership.user_id == current_user.id)
            .order_by(Organization.name)
        )
        result = await db.execute(stmt)
        orgs = result.scalars().all()

    responses = []
    for org in orgs:
        count = await _get_org_member_count(db, org.id)
        responses.append(
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                tier=org.tier,
                is_active=org.is_active,
                settings_json=org.settings_json,
                created_at=org.created_at,
                updated_at=org.updated_at,
                member_count=count,
            )
        )
    return responses


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Retrieve organization metadata by ID or slug",
)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Organization).where(
        (Organization.id == org_id) | (Organization.slug == org_id)
    )
    org = (await db.execute(stmt)).scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found.",
        )

    # Authorization check
    if not current_user.is_superuser:
        mem_stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == current_user.id,
        )
        if not (await db.execute(mem_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to organization '{org.name}'.",
            )

    count = await _get_org_member_count(db, org.id)
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        is_active=org.is_active,
        settings_json=org.settings_json,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=count,
    )


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to an organization",
)
async def add_organization_member(
    org_id: str,
    payload: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Lookup org
    org_stmt = select(Organization).where((Organization.id == org_id) | (Organization.slug == org_id))
    org = (await db.execute(org_stmt)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    # Authorization: Caller must be OWNER/ADMIN or Super Admin
    if not current_user.is_superuser:
        caller_mem = (
            await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == org.id,
                    OrganizationMembership.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if not caller_mem or caller_mem.role not in (MemberRole.OWNER.value, MemberRole.ADMIN.value):
            raise HTTPException(
                status_code=403,
                detail="Only organization owners and administrators can add members.",
            )

    # Find target user by email
    target_user = (
        await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    ).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with email '{payload.email}' not found.")

    # Check if already member
    existing_mem = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == target_user.id,
            )
        )
    ).scalar_one_or_none()
    if existing_mem:
        raise HTTPException(status_code=409, detail="User is already a member of this organization.")

    new_mem = OrganizationMembership(
        organization_id=org.id,
        user_id=target_user.id,
        role=payload.role.value,
    )
    db.add(new_mem)
    await db.commit()
    await db.refresh(new_mem)

    return MemberResponse(
        id=new_mem.id,
        organization_id=org.id,
        user_id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=new_mem.role,
        created_at=new_mem.created_at,
    )


@router.get(
    "/{org_id}/members",
    response_model=List[MemberResponse],
    summary="List members in an organization",
)
async def list_organization_members(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = (
        await db.execute(
            select(Organization).where((Organization.id == org_id) | (Organization.slug == org_id))
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    # Verify access
    if not current_user.is_superuser:
        has_access = (
            await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == org.id,
                    OrganizationMembership.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied.")

    stmt = (
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == org.id)
        .order_by(OrganizationMembership.created_at)
    )
    results = (await db.execute(stmt)).all()

    return [
        MemberResponse(
            id=mem.id,
            organization_id=org.id,
            user_id=usr.id,
            email=usr.email,
            full_name=usr.full_name,
            role=mem.role,
            created_at=mem.created_at,
        )
        for mem, usr in results
    ]


@router.post(
    "/switch",
    response_model=MessageResponse,
    summary="Switch active organization for the current user",
)
async def switch_organization(
    payload: SwitchOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = (
        await db.execute(
            select(Organization).where(
                (Organization.id == payload.organization_id) | (Organization.slug == payload.organization_id)
            )
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Target organization not found.")

    if not current_user.is_superuser:
        membership = (
            await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == org.id,
                    OrganizationMembership.user_id == current_user.id,
                )
            )
        ).scalar_one_or_none()
        if not membership:
            raise HTTPException(status_code=403, detail=f"You are not a member of '{org.name}'.")

    current_user.organization_id = org.id
    await db.commit()

    return MessageResponse(message=f"Successfully switched active organization context to '{org.name}' ({org.id}).")
