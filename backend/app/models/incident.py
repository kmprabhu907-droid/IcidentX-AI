"""
INCIDENTX AI - Incident SQLAlchemy Model
Represents the core incident lifecycle and operational metadata.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class Incident(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="SEV-2",
        index=True
    )  # SEV-1, SEV-2, SEV-3, SEV-4
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DETECTED",
        index=True
    )  # DETECTED, INVESTIGATING, MITIGATING, RESOLVED, CLOSED
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    impact_scope: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mttr_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="incident", cascade="all, delete-orphan"
    )
    hypotheses: Mapped[List["RootCauseHypothesis"]] = relationship(
        "RootCauseHypothesis", back_populates="incident", cascade="all, delete-orphan"
    )
    agent_executions: Mapped[List["AgentExecution"]] = relationship(
        "AgentExecution", back_populates="incident", cascade="all, delete-orphan"
    )
    remediation_actions: Mapped[List["RemediationAction"]] = relationship(
        "RemediationAction", back_populates="incident", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="incident"
    )
    telemetry_events: Mapped[List["TelemetryEvent"]] = relationship(
        "TelemetryEvent", back_populates="incident"
    )

    __table_args__ = (
        Index("idx_incident_status_severity", "status", "severity"),
    )
