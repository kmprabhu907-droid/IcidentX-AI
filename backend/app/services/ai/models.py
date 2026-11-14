"""
INCIDENTX AI - AI Reasoning & Multi-Provider Models (Phase 8.4)
Defines structured schemas for multi-provider health, token usage tracking,
evidence-grounded contracts, Root Cause Courtroom 2.0 verdicts, and reasoning reports.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderHealth(BaseModel):
    provider_name: str
    status: str = "NOT_CONFIGURED"  # AVAILABLE, UNAVAILABLE, NOT_CONFIGURED, DEGRADED, ERROR
    latency_ms: float = 0.0
    discovered_models: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ModelAttribution(BaseModel):
    provider_name: str
    model_name: str
    is_fallback: bool = False
    execution_time_ms: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AIReasoningEvidenceItem(BaseModel):
    evidence_id: str
    source_type: str  # KUBERNETES, PROMETHEUS, OPENTELEMETRY, LOG, DEMOMESH, RELIABILITY_MEMORY
    statement_classification: str = "OBSERVED_FACT"  # OBSERVED_FACT, DERIVED_CALCULATION, AI_HYPOTHESIS, RECOMMENDATION, UNKNOWN
    resource_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "SIMULATED"  # LIVE_K8S vs SIMULATED
    is_valid: bool = True


class CourtroomHypothesis(BaseModel):
    hypothesis_id: str
    culprit_service: Optional[str] = "cluster"
    title: str
    explanation: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    confidence_score: float = 0.5  # 0.0 - 1.0 calibrated
    is_leading: bool = False
    verification_status: str = "PROPOSED"  # PROPOSED, INVESTIGATED, VERIFIED, REJECTED, SUPERSEDED
    recommended_action: Optional[Dict[str, Any]] = None


class CourtroomVerdict(BaseModel):
    leading_hypothesis_id: str
    verdict_summary: str
    competing_hypotheses: List[CourtroomHypothesis] = Field(default_factory=list)
    counter_evidence_considered: List[str] = Field(default_factory=list)
    evidentiary_justification: str
    confidence_score: float = 0.5
    confidence_limitations: List[str] = Field(default_factory=list)
    model_attribution: ModelAttribution = Field(default_factory=lambda: ModelAttribution(provider_name="deterministic", model_name="incidentx-deterministic-v1"))


class AIIncidentReasoningReport(BaseModel):
    incident_id: str
    status: str = "COMPLETED"
    evidence_items: List[AIReasoningEvidenceItem] = Field(default_factory=list)
    courtroom_verdict: CourtroomVerdict
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    model_attribution: ModelAttribution
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AIUsageRecord(BaseModel):
    id: str
    incident_id: Optional[str] = None
    agent_name: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    is_fallback: bool = False
    status: str = "SUCCESS"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
