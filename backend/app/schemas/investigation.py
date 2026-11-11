"""
INCIDENTX AI - Investigation Pydantic Schemas
Defines serialization models for Evidence with provenance, Courtroom Hypotheses,
Agent Executions with versions, Investigation Plans, and Time Machine events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    id: str
    incident_id: str
    hypothesis_id: Optional[str] = None
    evidence_type: str
    source_system: str
    affected_service_name: Optional[str] = None
    raw_source_ref: Optional[str] = None
    description: str
    relevant_observation: Optional[str] = None
    confidence_score: float
    is_contradictory: bool
    verification_status: str = "VERIFIED"
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
    causal_chain: Optional[str] = None
    missing_evidence: Optional[str] = None
    evidence_count: int = 0
    contradiction_count: int = 0
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
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    thought_process: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[str] = None
    observation: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationPlanResponse(BaseModel):
    id: str
    incident_id: str
    recommended_actions: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimelineEventResponse(BaseModel):
    id: str
    incident_id: str
    timestamp: datetime
    event_type: str
    service_name: str
    title: str
    description: str
    severity: str
    data_source: str
    raw_data: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
