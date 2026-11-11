"""
INCIDENTX AI - Reliability Models
Provides persistent entities for Anomaly Records, Regression Records, and Predictive Warnings.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class AnomalyRecord(Base, UUIDMixin, TimestampMixin):
    """
    Persisted record of an anomaly detected by statistical, EWMA, or threshold engines.
    Extended in Stage 5.2 to track EWMA values, trend slopes, observation counts,
    and full lifecycle statuses (ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE).
    """
    __tablename__ = "anomaly_records"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    expected_baseline: Mapped[float] = mapped_column(Float, nullable=False)
    deviation: Mapped[float] = mapped_column(Float, nullable=False)
    ewma_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_slope: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="WARN")  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    detector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    supporting_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON or structured summary
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="SIMULATED")

    service: Mapped[Optional["Service"]] = relationship("Service")

    __table_args__ = (
        Index("idx_anomaly_service_time", "service_name", "detected_at"),
        Index("idx_anomaly_status", "status"),
    )


class RegressionRecord(Base, UUIDMixin, TimestampMixin):
    """
    Captures post-remediation regression events and recurring incident patterns.
    """
    __tablename__ = "regression_records"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    incident_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    post_remediation_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    regression_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DETECTED")  # DETECTED, INVESTIGATING, CONFIRMED, RESOLVED
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    service: Mapped[Optional["Service"]] = relationship("Service")
    incident: Mapped[Optional["Incident"]] = relationship("Incident")

    __table_args__ = (
        Index("idx_regression_service_time", "service_name", "detected_at"),
    )


class PredictiveWarning(Base, UUIDMixin, TimestampMixin):
    """
    Evidence-based proactive warning for resource exhaustion or creeping degradation.
    """
    __tablename__ = "predictive_warnings"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    warning_type: Mapped[str] = mapped_column(String(50), nullable=False)  # RESOURCE_EXHAUSTION, CONNECTION_CREEP, LATENCY_DRIFT
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    projected_time_to_exhaustion_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    supporting_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant_time_window: Mapped[str] = mapped_column(String(50), nullable=False, default="15m")
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    emitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    service: Mapped[Optional["Service"]] = relationship("Service")

    __table_args__ = (
        Index("idx_warning_service_time", "service_name", "emitted_at"),
    )
