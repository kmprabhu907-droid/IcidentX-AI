"""
INCIDENTX AI - Workflow Execution Models (Stage 6.5)
Implements state machine tracking for end-to-end autonomous reliability workflows.
"""

from datetime import datetime, timezone
import enum
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base


class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False, default="default-org"
    )
    incident_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="SET NULL"), index=True, nullable=True
    )
    workflow_type: Mapped[str] = mapped_column(
        String(100), default="AUTONOMOUS_INCIDENT_REMEDIATION", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=WorkflowStatus.PENDING.value, index=True, nullable=False
    )
    current_step: Mapped[str] = mapped_column(String(100), default="DETECTION", nullable=False)
    step_history_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
