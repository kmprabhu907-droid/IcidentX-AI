"""
INCIDENTX AI - Alert SQLAlchemy Model (Phase 9)
Stores inbound alerts from Prometheus Alertmanager, Grafana, Kubernetes events,
OpenTelemetry signals, and webhooks with fingerprint deduplication and correlation.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"

    incident_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    alert_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="alertmanager", index=True
    )  # alertmanager, grafana, kubernetes, opentelemetry, manual, webhook
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="P2", index=True
    )  # P1, P2, P3, P4
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DEMOMESH", index=True
    )  # DEMOMESH or KUBERNETES
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE, CORRELATED, SUPPRESSED, RESOLVED
    description: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to parent incident
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="alerts")

    __table_args__ = (
        Index("idx_alert_fingerprint_status", "fingerprint", "status"),
        Index("idx_alert_service_time", "service_name", "starts_at"),
    )
