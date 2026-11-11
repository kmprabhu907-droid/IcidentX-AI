"""
INCIDENTX AI - Audit Log SQLAlchemy Model
Provides tamper-evident, cryptographically chained record of all system events,
agent decisions, and human actions.
"""

from typing import Optional
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_logs"

    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, default="default-org", index=True
    )
    incident_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SYSTEM, AGENT, USER
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)  # User ID, Agent Role, or Service Name
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Cryptographic Hash Chaining for Tamper-Evidence
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_actor_action", "actor_type", "action"),
        Index("idx_audit_org_action", "organization_id", "action"),
    )
