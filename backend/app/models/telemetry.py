"""
INCIDENTX AI - Telemetry Event SQLAlchemy Model
Captures discrete metric anomalies, logs, and span events linked to services and incidents.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class TelemetryEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "telemetry_events"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    incident_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # metric_spike, error_log, trace_span, alert
    metric_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")  # INFO, WARN, CRITICAL
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    service: Mapped[Optional["Service"]] = relationship("Service", back_populates="telemetry_events")
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="telemetry_events")

    __table_args__ = (
        Index("idx_telemetry_event_time", "event_type", "timestamp"),
    )
