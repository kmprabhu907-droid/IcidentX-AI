"""
INCIDENTX AI - Service & Dependency SQLAlchemy Models
Represents microservices, infrastructure nodes, and their topology relationships.
"""

from typing import List, Optional
from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class Service(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="Tier-2")  # Tier-1, Tier-2, Tier-3
    service_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="service"
    )  # gateway, service, database, cache, queue
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Go, Rust, Python, TypeScript
    health_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="HEALTHY", index=True
    )  # HEALTHY, DEGRADED, CRITICAL
    repository_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    dependencies_outbound: Mapped[List["ServiceDependency"]] = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.source_service_id",
        back_populates="source_service",
        cascade="all, delete-orphan",
    )
    dependencies_inbound: Mapped[List["ServiceDependency"]] = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.target_service_id",
        back_populates="target_service",
        cascade="all, delete-orphan",
    )
    telemetry_events: Mapped[List["TelemetryEvent"]] = relationship(
        "TelemetryEvent", back_populates="service"
    )


class ServiceDependency(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "service_dependencies"

    source_service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_service_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    protocol: Mapped[str] = mapped_column(String(50), nullable=False, default="HTTP")  # HTTP, gRPC, TCP, Kafka
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source_service: Mapped["Service"] = relationship(
        "Service", foreign_keys=[source_service_id], back_populates="dependencies_outbound"
    )
    target_service: Mapped["Service"] = relationship(
        "Service", foreign_keys=[target_service_id], back_populates="dependencies_inbound"
    )

    __table_args__ = (
        UniqueConstraint("source_service_id", "target_service_id", name="uq_service_dependency_pair"),
        Index("idx_dependency_pair", "source_service_id", "target_service_id"),
    )
