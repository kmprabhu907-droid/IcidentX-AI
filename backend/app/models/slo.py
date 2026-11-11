"""
INCIDENTX AI - Service Level Objective (SLO) SQLAlchemy Models
Defines service-level objectives, targets, and calculated error budget measurements.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class SLODefinition(Base, UUIDMixin, TimestampMixin):
    """
    Defines target Service Level Objectives for individual microservices.
    Supports availability, latency, and error rate objectives with configurable windows.
    """
    __tablename__ = "slo_definitions"

    service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default="default-org", index=True
    )
    slo_type: Mapped[str] = mapped_column(String(50), nullable=False)  # availability, latency, error_rate
    target_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=99.9)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g., 200.0 ms for latency
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    service: Mapped[Optional["Service"]] = relationship("Service")
    measurements: Mapped[List["SLOMeasurement"]] = relationship(
        "SLOMeasurement", back_populates="slo", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_slo_service_type", "service_name", "slo_type"),
    )


class SLOMeasurement(Base, UUIDMixin, TimestampMixin):
    """
    Point-in-time calculation of SLI compliance, remaining error budget, and burn rate.
    """
    __tablename__ = "slo_measurements"

    slo_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("slo_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    current_sli: Mapped[float] = mapped_column(Float, nullable=False)
    error_budget_remaining: Mapped[float] = mapped_column(Float, nullable=False)
    error_budget_consumed: Mapped[float] = mapped_column(Float, nullable=False)
    burn_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    slo: Mapped["SLODefinition"] = relationship("SLODefinition", back_populates="measurements")
