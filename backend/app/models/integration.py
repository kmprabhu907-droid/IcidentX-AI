"""
INCIDENTX AI - Enterprise Integration Models (Stage 6.4)
Stores connector configurations for Slack, PagerDuty, GitHub, Jira, and Generic Webhooks.
"""

from datetime import datetime, timezone
import enum
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base


class IntegrationProvider(str, enum.Enum):
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    GITHUB = "github"
    JIRA = "jira"
    WEBHOOK = "webhook"


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False, default="default-org"
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    events_subscribed: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["INCIDENT_DETECTED", "RCA_COMPLETED", "REMEDIATION_APPROVAL_REQUESTED", "REMEDIATION_EXECUTED", "REGRESSION_DETECTED"]'
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
