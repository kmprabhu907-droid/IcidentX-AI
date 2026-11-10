"""
INCIDENTX AI - Audit Log Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: str
    incident_id: Optional[str] = None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
