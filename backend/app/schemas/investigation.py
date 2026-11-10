"""
INCIDENTX AI - Investigation Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    id: str
    incident_id: str
    evidence_type: str
    source_system: str
    description: str
    confidence_score: float
    is_contradictory: bool
    observed_at: datetime
    raw_data: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HypothesisResponse(BaseModel):
    id: str
    incident_id: str
    culprit_service_id: Optional[str] = None
    hypothesis_text: str
    probability_score: float
    status: str
    prosecutor_argument: Optional[str] = None
    defense_argument: Optional[str] = None
    judicial_ruling: Optional[str] = None
    is_confirmed_root_cause: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentExecutionResponse(BaseModel):
    id: str
    incident_id: str
    agent_role: str
    execution_phase: str
    status: str
    thought_process: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[str] = None
    observation: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
