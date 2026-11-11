"""
INCIDENTX AI - User & Access Management Models (Stage 6.2)
Implements User entities, 6-tier RBAC role definitions, and rotating refresh tokens.
"""

from datetime import datetime, timezone
import enum
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base


class UserRole(str, enum.Enum):
    """6 Enterprise RBAC roles for IncidentX AI."""
    SUPER_ADMIN = "SUPER_ADMIN"
    ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
    SRE_ENGINEER = "SRE_ENGINEER"
    INCIDENT_RESPONDER = "INCIDENT_RESPONDER"
    SECURITY_AUDITOR = "SECURITY_AUDITOR"
    READ_ONLY_VIEWER = "READ_ONLY_VIEWER"


# Role Permission Hierarchy
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: {
        "admin:all",
        "org:manage",
        "users:manage",
        "incidents:read",
        "incidents:write",
        "investigation:run",
        "remediation:approve",
        "remediation:execute",
        "remediation:rollback",
        "simulation:execute",
        "slo:manage",
        "audit:read",
    },
    UserRole.ORGANIZATION_ADMIN: {
        "org:manage",
        "users:manage",
        "incidents:read",
        "incidents:write",
        "investigation:run",
        "remediation:approve",
        "remediation:execute",
        "remediation:rollback",
        "simulation:execute",
        "slo:manage",
        "audit:read",
    },
    UserRole.SRE_ENGINEER: {
        "incidents:read",
        "incidents:write",
        "investigation:run",
        "remediation:approve",
        "remediation:execute",
        "remediation:rollback",
        "simulation:execute",
        "slo:manage",
        "audit:read",
    },
    UserRole.INCIDENT_RESPONDER: {
        "incidents:read",
        "incidents:write",
        "investigation:run",
        "remediation:approve",
        "audit:read",
    },
    UserRole.SECURITY_AUDITOR: {
        "incidents:read",
        "audit:read",
        "slo:read",
    },
    UserRole.READ_ONLY_VIEWER: {
        "incidents:read",
        "slo:read",
    },
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default=UserRole.READ_ONLY_VIEWER.value, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def has_permission(self, permission: str) -> bool:
        if self.is_superuser:
            return True
        try:
            role_enum = UserRole(self.role)
            return permission in ROLE_PERMISSIONS.get(role_enum, set())
        except ValueError:
            return False


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user = relationship("User", back_populates="refresh_tokens")
