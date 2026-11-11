"""
INCIDENTX AI - Reliability Memory Models & Schemas
Typed data models for historical incident memory retrieval,
fingerprint similarity explanations, and remediation learning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class HistoricalMemoryEntry:
    """Complete aggregated historical incident memory across all 20 dimensions."""
    incident_id: str
    title: str
    summary: str
    severity: str
    status: str
    detected_at: Optional[str]
    resolved_at: Optional[str]
    mttr_seconds: Optional[float]
    primary_service: str
    affected_services: List[str] = field(default_factory=list)
    root_cause_category: str = "UNKNOWN"
    confirmed_root_cause: Optional[str] = None
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    telemetry_patterns: Dict[str, float] = field(default_factory=dict)
    error_signatures: List[str] = field(default_factory=list)
    dependency_relationships: Dict[str, List[str]] = field(default_factory=dict)
    remediation_actions: List[Dict[str, Any]] = field(default_factory=list)
    remediation_outcome: str = "UNKNOWN"  # SUSTAINED_SUCCESS, TEMPORARY_SUCCESS, FAILED
    learned_lessons: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    regressions_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "summary": self.summary,
            "severity": self.severity,
            "status": self.status,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "mttr_seconds": self.mttr_seconds,
            "primary_service": self.primary_service,
            "affected_services": self.affected_services,
            "root_cause_category": self.root_cause_category,
            "confirmed_root_cause": self.confirmed_root_cause,
            "hypotheses": self.hypotheses,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "telemetry_patterns": self.telemetry_patterns,
            "error_signatures": self.error_signatures,
            "dependency_relationships": self.dependency_relationships,
            "remediation_actions": self.remediation_actions,
            "remediation_outcome": self.remediation_outcome,
            "learned_lessons": self.learned_lessons,
            "side_effects": self.side_effects,
            "regressions_count": self.regressions_count,
        }


@dataclass
class MemorySearchExplanation:
    """The 6 standard explanations for a retrieved historical memory entry."""
    why_selected: str
    similarity_score: float
    evidence_matches: List[str] = field(default_factory=list)
    evidence_differs: List[str] = field(default_factory=list)
    previous_remediation_effective: str = "UNKNOWN"
    reusable_lessons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "why_selected": self.why_selected,
            "similarity_score": round(self.similarity_score, 3),
            "evidence_matches": self.evidence_matches,
            "evidence_differs": self.evidence_differs,
            "previous_remediation_effective": self.previous_remediation_effective,
            "reusable_lessons": self.reusable_lessons,
        }


@dataclass
class RemediationLearningSummary:
    """Historical learning from executing a specific remediation action."""
    action_id: str
    action_name: str
    target_service: str
    total_executions: int
    success_rate: float
    sustained_success_count: int
    temporary_success_count: int
    failed_count: int
    rollback_count: int
    recurrence_count: int
    known_side_effects: List[str] = field(default_factory=list)
    reusable_advice: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "target_service": self.target_service,
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 2),
            "sustained_success_count": self.sustained_success_count,
            "temporary_success_count": self.temporary_success_count,
            "failed_count": self.failed_count,
            "rollback_count": self.rollback_count,
            "recurrence_count": self.recurrence_count,
            "known_side_effects": self.known_side_effects,
            "reusable_advice": self.reusable_advice,
        }
