"""
INCIDENTX AI - Remediation Action SQLAlchemy Model
Tracks proposed and executed interventions, risk tiers, and approval states.
"""

from typing import Optional
from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class RemediationAction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "remediation_actions"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hypothesis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("root_cause_hypotheses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # k8s_rollout_undo, restart_pool, scale_replicas, traffic_drain
    target_service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    command_payload: Mapped[str] = mapped_column(Text, nullable=False)
    risk_tier: Mapped[str] = mapped_column(
        String(30), nullable=False, default="TIER_1_LOW"
    )  # TIER_0_READONLY, TIER_1_LOW, TIER_2_MEDIUM, TIER_3_HIGH
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PROPOSED", index=True
    )  # PROPOSED, SIMULATING, APPROVED, REJECTED, EXECUTED, VERIFIED
    approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING, APPROVED, DENIED, EXPIRED
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attestation_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    simulated_slo_recovery: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    simulated_blast_radius: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="remediation_actions")
    hypothesis: Mapped[Optional["RootCauseHypothesis"]] = relationship("RootCauseHypothesis", back_populates="remediation_actions")

    __table_args__ = (
        Index("idx_remediation_risk_status", "risk_tier", "status"),
    )
