"""
INCIDENTX AI - Multi-Tenant Resolution & Scoping Engine (Stage 6.3)
Provides organization resolution, header inspection (X-Organization-ID), and tenant data isolation.
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import get_current_user, get_optional_current_user
from backend.app.core.database import get_db
from backend.app.models.organization import (
    MemberRole,
    Organization,
    OrganizationMembership,
    OrganizationTier,
)
from backend.app.models.user import User


DEFAULT_ORG_ID = "default-org"
DEFAULT_ORG_SLUG = "default"
DEFAULT_ORG_NAME = "Default Organization"


async def ensure_default_organization(db: AsyncSession) -> Organization:
    """Ensures the baseline default tenant organization exists in persistence."""
    stmt = select(Organization).where(
        (Organization.id == DEFAULT_ORG_ID) | (Organization.slug == DEFAULT_ORG_SLUG)
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()
    if not org:
        org = Organization(
            id=DEFAULT_ORG_ID,
            name=DEFAULT_ORG_NAME,
            slug=DEFAULT_ORG_SLUG,
            tier=OrganizationTier.ENTERPRISE.value,
            is_active=True,
            settings_json='{"description": "Root multi-tenant default workspace"}',
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
    return org


async def get_current_tenant(
    x_org_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Resolves the current organization context for the request.
    Priority:
    1. Explicit 'X-Organization-ID' header (UUID or slug)
    2. Authenticated user's active organization_id
    3. Default system organization fallback
    """
    target_id = x_org_id or (current_user.organization_id if current_user else None) or DEFAULT_ORG_ID

    stmt = select(Organization).where(
        (Organization.id == target_id) | (Organization.slug == target_id)
    )
    result = await db.execute(stmt)
    org = result.scalar_one_or_none()

    if not org:
        if target_id == DEFAULT_ORG_ID:
            org = await ensure_default_organization(db)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with identifier '{target_id}' not found.",
            )

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization '{org.name}' is suspended or inactive.",
        )

    # If user is authenticated, verify tenant membership boundary
    if current_user and not current_user.is_superuser:
        # Check membership
        mem_stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == current_user.id,
        )
        mem_result = await db.execute(mem_stmt)
        membership = mem_result.scalar_one_or_none()

        # If user is not member and target is not their assigned org, deny
        if not membership and current_user.organization_id != org.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User lacks active membership in organization '{org.name}'.",
            )

    return org
