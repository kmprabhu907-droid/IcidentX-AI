"""
INCIDENTX AI - Incident Time Machine Timeline Event Model
Stores discrete historical events across metric anomalies, errors, latency, logs, traces,
deployments, and health transitions for full timeline reconstruction and replay.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class TimelineEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "timeline_events"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # METRIC_ANOMALY, ERROR_SURGE, LATENCY_SPIKE, LOG_ERROR, TRACE_FAILURE, DEPLOYMENT, CONFIG_CHANGE, HEALTH_CHANGE, DETECTION, RECOVERY
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")  # INFO, WARN, CRITICAL
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="SYSTEM")
    actor_type: Mapped[str] = mapped_column(String(30), nullable=False, default="SYSTEM")  # AI_AGENT, HUMAN, SYSTEM
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="LIVE")  # LIVE or SIMULATED
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="timeline_events")

    __table_args__ = (
        Index("idx_timeline_incident_time", "incident_id", "timestamp"),
        Index("idx_timeline_type_time", "event_type", "timestamp"),
    )
