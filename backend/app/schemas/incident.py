"""
INCIDENTX AI - Incident Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Incident title")
    summary: Optional[str] = Field(None, description="Detailed incident summary / description")
    severity: str = Field(default="SEV-2", pattern="^(SEV-1|SEV-2|SEV-3|SEV-4)$", description="Severity tier")
    status: str = Field(default="DETECTED", pattern="^(DETECTED|INVESTIGATING|MITIGATING|RESOLVED|CLOSED)$")
    impact_scope: Optional[str] = Field(None, max_length=255, description="Affected user/service surface area")


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    summary: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(SEV-1|SEV-2|SEV-3|SEV-4)$")
    status: Optional[str] = Field(None, pattern="^(DETECTED|INVESTIGATING|MITIGATING|RESOLVED|CLOSED)$")
    impact_scope: Optional[str] = None
    resolved_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None


class IncidentResponse(IncidentBase):
    id: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
