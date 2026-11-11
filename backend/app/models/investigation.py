"""
INCIDENTX AI - Investigation Domain SQLAlchemy Models
Includes Evidence exhibits with provenance, Root Cause Hypotheses (Courtroom),
Agent Executions with versioning, and Active Investigation Plans.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base, TimestampMixin, UUIDMixin


class Evidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "evidence"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hypothesis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("root_cause_hypotheses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # metric_anomaly, error_log, trace_span, git_commit, kernel_lock
    source_system: Mapped[str] = mapped_column(String(100), nullable=False)  # prometheus, loki, opentelemetry, github
    affected_service_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    raw_source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # trace_id, span_id, log_id
    description: Mapped[str] = mapped_column(Text, nullable=False)
    relevant_observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_contradictory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="VERIFIED"
    )  # VERIFIED, CONTRADICTED, UNVERIFIED, INSUFFICIENT
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="evidence_items")
    hypothesis: Mapped[Optional["RootCauseHypothesis"]] = relationship(
        "RootCauseHypothesis", back_populates="evidence_items"
    )


class RootCauseHypothesis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "root_cause_hypotheses"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    culprit_service_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hypothesis_text: Mapped[str] = mapped_column(Text, nullable=False)
    probability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PROPOSED", index=True
    )  # PROPOSED, UNDER_CROSS_EXAMINATION, VALIDATED, DISPROVEN, INSUFFICIENT_EVIDENCE
    prosecutor_argument: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    defense_argument: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    judicial_ruling: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    causal_chain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Detailed causal progression
    missing_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Evidence gaps needed
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_confirmed_root_cause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="hypotheses")
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="hypothesis"
    )
    remediation_actions: Mapped[List["RemediationAction"]] = relationship(
        "RemediationAction", back_populates="hypothesis"
    )


class AgentExecution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_executions"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_role: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # intake, context, telemetry, log, trace, dependency, deployment, hypothesis, verification, summary
    execution_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", index=True
    )  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    thought_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_arguments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="agent_executions")

    __table_args__ = (
        Index("idx_agent_incident_role", "incident_id", "agent_role"),
    )


class InvestigationPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "investigation_plans"

    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recommended_actions: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string of diagnostic actions
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RECOMMENDED"
    )  # RECOMMENDED, EXECUTED, DISMISSED

    incident: Mapped["Incident"] = relationship("Incident", back_populates="investigation_plans")
