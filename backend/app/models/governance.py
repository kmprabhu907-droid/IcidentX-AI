"""
INCIDENTX AI - Governance & Operational Policy SQLAlchemy Models
Supports configurable data retention, approval requirements, AI execution permissions,
and organization capacity limits.
"""

from typing import Optional
from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class GovernancePolicy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "governance_policies"

    organization_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default="default-org", index=True
    )
    policy_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # DATA_RETENTION, APPROVAL_POLICY, AI_EXECUTION_PERMISSION, ORG_LIMITS
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON encoded rules
    is_enforced: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    __table_args__ = (
        Index("idx_gov_org_type", "organization_id", "policy_type"),
    )
