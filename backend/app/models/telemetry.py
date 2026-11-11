"""
INCIDENTX AI - Telemetry Event SQLAlchemy Model
Captures discrete metric anomalies, logs, and span events linked to services and incidents.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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


class MetricRollup(Base, UUIDMixin, TimestampMixin):
    """
    Downsampled 1-minute time-bucket metric rollup.
    Prevents unbounded raw telemetry storage while preserving minimum, maximum,
    average, and latest point-in-time statistics for historical lookbacks.
    """
    __tablename__ = "metric_rollups"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    minimum: Mapped[float] = mapped_column(Float, nullable=False)
    maximum: Mapped[float] = mapped_column(Float, nullable=False)
    average: Mapped[float] = mapped_column(Float, nullable=False)
    latest_value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="SIMULATED")

    service: Mapped[Optional["Service"]] = relationship("Service")

    __table_args__ = (
        UniqueConstraint("service_name", "metric_name", "bucket_start", name="uq_metric_rollup_bucket"),
        Index("idx_rollup_service_metric_time", "service_name", "metric_name", "bucket_start"),
    )
