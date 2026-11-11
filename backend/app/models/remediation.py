"""
INCIDENTX AI - Remediation Action & Policy SQLAlchemy Models
Tracks proposed and executed interventions, risk tiers, approval states,
execution modes, idempotency keys, verification snapshots, and rollback lifecycles.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class RemediationAction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "remediation_actions"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), nullable=False, default="default-org", index=True
    )
    hypothesis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("root_cause_hypotheses.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Action definition from registry
    action_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g. act-restart-service
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # restart, scale, rollback, cache, db_pool, flag, rate_limit, switch_dep
    target_service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )

    # Validated parameters and preconditions (JSON serialized)
    parameters: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    preconditions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)

    # Safety, Risk & Intelligence
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    risk_tier: Mapped[str] = mapped_column(String(30), nullable=False, default="TIER_1_LOW")  # Legacy compatibility
    estimated_cost: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW")  # LOW, MEDIUM, HIGH
    expected_benefit: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)  # 0.0 to 1.0
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contraindications: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list of disallowed alternative actions

    # Execution Mode & Safety Policy
    execution_mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RECOMMENDATION_ONLY"
    )  # RECOMMENDATION_ONLY, HUMAN_APPROVAL, CONTROLLED_AUTONOMOUS
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    # Approval State
    approval_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", index=True
    )  # PENDING, APPROVED, REJECTED, EXPIRED, NOT_REQUIRED
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution State
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PROPOSED", index=True
    )  # PROPOSED, APPROVED, REJECTED, EXECUTING, EXECUTED, FAILED, CANCELLED
    command_payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # Non-destructive command or payload representation
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    execution_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Snapshots & Empirical Telemetry Verification
    snapshot_before: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_after: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", index=True
    )  # PENDING, VERIFIED, PARTIALLY_VERIFIED, FAILED, INCONCLUSIVE
    verification_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON delta report

    # Rollback Control
    rollback_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NONE"
    )  # NONE, AVAILABLE, EXECUTING, ROLLED_BACK, ROLLBACK_FAILED
    rollback_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Errors & Diagnostics
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="remediation_actions")
    hypothesis: Mapped[Optional["RootCauseHypothesis"]] = relationship(
        "RootCauseHypothesis", back_populates="remediation_actions"
    )

    __table_args__ = (
        Index("idx_remediation_risk_status", "risk_level", "status"),
        Index("idx_remediation_incident_status", "incident_id", "status"),
    )


class RemediationPolicy(Base, UUIDMixin, TimestampMixin):
    """
    Global and per-tenant safety policy controlling remediation execution modes,
    allowlists, budgets, and circuit breaker trip states.
    """
    __tablename__ = "remediation_policies"

    name: Mapped[str] = mapped_column(String(100), default="global-default", unique=True, index=True)
    mode: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RECOMMENDATION_ONLY"
    )  # RECOMMENDATION_ONLY (Default), HUMAN_APPROVAL, CONTROLLED_AUTONOMOUS
    is_autonomous_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allowlisted_action_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["act-clear-cache", "act-scale-replicas", "act-toggle-feature-flag", "act-apply-rate-limit", "act-restart-service"]'
    )
    max_actions_per_incident: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    circuit_breaker_tripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    circuit_breaker_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergency_stop_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
