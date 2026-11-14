"""
INCIDENTX AI - Phase 11 Root Cause Intelligence Schemas
Defines structured data models for Hypotheses, Competing Evaluation,
Causal Graphs, Counter-Evidence Disproof, and Historical Intelligence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    INVESTIGATING = "INVESTIGATING"
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONFIRMED = "CONFIRMED"


class ConfidenceCategory(str, Enum):
    VERY_HIGH = "VERY_HIGH"                  # score >= 0.85
    HIGH = "HIGH"                            # 0.70 - 0.84
    MODERATE = "MODERATE"                    # 0.50 - 0.69
    LOW = "LOW"                              # 0.25 - 0.49
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # < 0.25


class CausalNodeType(str, Enum):
    TRIGGERING_EVENT = "TRIGGERING_EVENT"
    INTERMEDIATE_FAILURE = "INTERMEDIATE_FAILURE"
    CONTRIBUTING_FACTOR = "CONTRIBUTING_FACTOR"
    AFFECTED_SERVICE = "AFFECTED_SERVICE"
    CASCADING_FAILURE = "CASCADING_FAILURE"
    USER_FACING_SYMPTOM = "USER_FACING_SYMPTOM"
    ROOT_CAUSE_CANDIDATE = "ROOT_CAUSE_CANDIDATE"


class CausalRelationType(str, Enum):
    VERIFIED_CAUSAL = "VERIFIED_CAUSAL"          # Proven by direct telemetry & temporal sequence
    INFERRED_CORRELATION = "INFERRED_CORRELATION"  # Correlated signals without direct mechanism trace
    ASSUMPTION = "ASSUMPTION"                      # Working hypothesis gap requiring validation


class HypothesisItem(BaseModel):
    id: str
    incident_id: str
    investigation_id: Optional[str] = None
    title: str
    description: str
    affected_service: str
    triggering_event: Optional[str] = None
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    source_domains: List[str] = Field(default_factory=list)
    confidence_score: float = 0.50
    confidence_category: ConfidenceCategory = ConfidenceCategory.MODERATE
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    score_breakdown: Optional[Dict[str, Any]] = None
    causal_chain_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CompetingHypothesisAnalysis(BaseModel):
    incident_id: str
    investigation_id: Optional[str] = None
    total_hypotheses: int
    ranked_hypotheses: List[HypothesisItem]
    shared_evidence_matrix: Dict[str, List[str]] = Field(default_factory=dict)
    discriminating_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    conflicting_evidence_notes: List[str] = Field(default_factory=list)
    unsupported_assumptions: Dict[str, List[str]] = Field(default_factory=dict)
    ranking_rationale: str
    top_hypothesis_id: Optional[str] = None


class CounterEvidenceReport(BaseModel):
    hypothesis_id: str
    hypothesis_title: str
    disproof_attempted: bool = True
    counter_evidence_found: List[str] = Field(default_factory=list)
    missing_expected_evidence: List[str] = Field(default_factory=list)
    verdict: str  # SURVIVED_DISPROOF, WEAKENED, REFUTED
    score_penalty_applied: float = 0.0
    rationale: str


class CausalNode(BaseModel):
    id: str
    label: str
    node_type: CausalNodeType
    service_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_empirical_fact: bool = True
    evidence_id: Optional[str] = None


class CausalEdge(BaseModel):
    source: str
    target: str
    relationship: str  # TRIGGERS, CAUSES, CONTRIBUTES_TO, EXACERBATES, RESULTS_IN
    relation_type: CausalRelationType
    confidence: float = 1.0


class CausalGraph(BaseModel):
    incident_id: str
    nodes: List[CausalNode]
    edges: List[CausalEdge]
    triggering_event: Optional[str] = None
    root_cause_candidate: Optional[str] = None
    verified_causal_ratio: float = 1.0


class SimilarIncidentMatch(BaseModel):
    incident_id: str
    title: str
    severity: str
    similarity_score: float  # 0.0 to 1.0
    matching_service: str
    identified_root_cause: Optional[str] = None
    remediation_applied: Optional[str] = None
    remediation_successful: bool = True
    detected_at: datetime


class RootCauseReport(BaseModel):
    incident_id: str
    investigation_id: Optional[str] = None
    primary_root_cause: str
    primary_hypothesis: HypothesisItem
    competing_analysis: CompetingHypothesisAnalysis
    counter_evidence_reports: List[CounterEvidenceReport]
    causal_graph: CausalGraph
    similar_incidents: List[SimilarIncidentMatch]
    is_recurrence: bool = False
    recurrence_count: int = 0
    confidence_score: float
    confidence_category: ConfidenceCategory
    executive_summary: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
