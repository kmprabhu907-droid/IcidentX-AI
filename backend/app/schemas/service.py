"""
INCIDENTX AI - Service & Dependency Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Unique microservice name")
    tier: str = Field(default="Tier-2", pattern="^(Tier-1|Tier-2|Tier-3)$")
    service_type: str = Field(default="service", pattern="^(gateway|service|database|cache|queue|mesh)$")
    language: Optional[str] = Field(None, max_length=50)
    health_status: str = Field(default="HEALTHY", pattern="^(HEALTHY|DEGRADED|CRITICAL)$")
    repository_url: Optional[str] = Field(None, max_length=255)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    tier: Optional[str] = Field(None, pattern="^(Tier-1|Tier-2|Tier-3)$")
    service_type: Optional[str] = Field(None, pattern="^(gateway|service|database|cache|queue|mesh)$")
    language: Optional[str] = None
    health_status: Optional[str] = Field(None, pattern="^(HEALTHY|DEGRADED|CRITICAL)$")
    repository_url: Optional[str] = None


class ServiceResponse(ServiceBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DependencyCreate(BaseModel):
    source_service_id: str = Field(..., description="UUID of upstream caller service")
    target_service_id: str = Field(..., description="UUID of downstream dependency service")
    protocol: str = Field(default="HTTP", max_length=50, description="Protocol: HTTP, gRPC, TCP, Kafka")
    is_critical: bool = Field(default=True, description="Whether failure of target breaks source service")


class DependencyResponse(BaseModel):
    id: str
    source_service_id: str
    target_service_id: str
    protocol: str
    is_critical: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
