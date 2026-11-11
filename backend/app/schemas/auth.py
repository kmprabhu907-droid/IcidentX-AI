"""
INCIDENTX AI - Authentication & RBAC Pydantic Schemas (Stage 6.2)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from backend.app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 character password")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: Optional[UserRole] = Field(default=UserRole.READ_ONLY_VIEWER)
    organization_id: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    organization_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    permissions: List[str] = []

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
