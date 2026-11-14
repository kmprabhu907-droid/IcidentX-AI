"""
INCIDENTX AI - Incident Ownership & Assignment Model (Phase 9)
Tracks engineer, responder, and team ownership changes, reassignment rationales,
and escalation paths across the incident lifecycle.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class IncidentAssignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incident_assignments"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    assigned_to_name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Platform SRE")
    assigned_by: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PRIMARY_RESPONDER"
    )  # PRIMARY_RESPONDER, SECONDARY_SRE, INCIDENT_COMMANDER
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="assignments")

    __table_args__ = (
        Index("idx_assignment_incident_user", "incident_id", "assigned_to_id"),
    )
