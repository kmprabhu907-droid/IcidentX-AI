"""
INCIDENTX AI - Organization Pydantic Schemas (Stage 6.3)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.models.organization import MemberRole, OrganizationTier


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-z0-9-]+$')
    tier: Optional[OrganizationTier] = Field(default=OrganizationTier.ENTERPRISE)
    settings_json: Optional[str] = "{}"


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = None
    tier: Optional[OrganizationTier] = None
    is_active: Optional[bool] = None
    settings_json: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    tier: str
    is_active: bool
    settings_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class MemberAddRequest(BaseModel):
    email: str
    role: MemberRole = MemberRole.MEMBER


class MemberResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SwitchOrganizationRequest(BaseModel):
    organization_id: str
