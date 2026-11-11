"""
INCIDENTX AI - Incident Time Machine Models (Stage 5.7)
Defines timeline entries, state snapshots, causal graph structures, and historical replay reports.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    """Chronologically sorted event along the incident lifecycle."""
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    phase: str = Field(..., description="PRE_INCIDENT, DETECTION, INVESTIGATION, REMEDIATION, VERIFICATION, POST_RECOVERY, REGRESSION")
    event_type: str = Field(..., description="METRIC_SAMPLE, ANOMALY_ALERT, LOG_RECORD, TRACE_SPAN, HYPOTHESIS_FORMED, ACTION_EXECUTED, VERIFICATION_PASSED, REGRESSION_DETECTED")
    source_service: str
    summary: str
    severity: str  # INFO, WARN, CRITICAL
    details: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "phase": self.phase,
            "event_type": self.event_type,
            "source_service": self.source_service,
            "summary": self.summary,
            "severity": self.severity,
            "details": self.details,
        }


class PhaseStateSnapshot(BaseModel):
    """Point-in-time infrastructure metrics and operational health."""
    phase: str
    timestamp: str
    service_metrics: Dict[str, Dict[str, float]]
    active_anomalies_count: int
    overall_health: str  # HEALTHY, DEGRADED, CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "service_metrics": self.service_metrics,
            "active_anomalies_count": self.active_anomalies_count,
            "overall_health": self.overall_health,
        }


class CausalNode(BaseModel):
    """NetworkX dependency graph node annotated with health and failure attribution."""
    id: str
    label: str
    service_type: str
    health_status: str  # HEALTHY, DEGRADED, FAILING
    anomaly_score: float
    is_root_cause_candidate: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "service_type": self.service_type,
            "health_status": self.health_status,
            "anomaly_score": round(self.anomaly_score, 2),
            "is_root_cause_candidate": self.is_root_cause_candidate,
        }


class CausalEdge(BaseModel):
    """Directed dependency edge representing call flow and failure cascade."""
    source: str
    target: str
    relationship: str
    latency_ms: float
    is_impact_path: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relationship": self.relationship,
            "latency_ms": round(self.latency_ms, 2),
            "is_impact_path": self.is_impact_path,
        }


class CausalGraphState(BaseModel):
    """Complete causal topology state with failure propagation paths."""
    phase: str
    timestamp: str
    nodes: List[CausalNode] = Field(default_factory=list)
    edges: List[CausalEdge] = Field(default_factory=list)
    impacted_path: List[str] = Field(default_factory=list)
    blast_radius_score: float = Field(0.0, description="0.0 to 100.0 topology impact score")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "impacted_path": self.impacted_path,
            "blast_radius_score": round(self.blast_radius_score, 1),
        }


class IncidentReplayReport(BaseModel):
    """Complete historical reconstruction of an incident from inception to post-recovery."""
    incident_id: str
    title: str
    lifecycle_phases: List[str]
    timeline_events: List[TimelineEntry]
    state_transitions: Dict[str, PhaseStateSnapshot]
    causal_graph: CausalGraphState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "lifecycle_phases": self.lifecycle_phases,
            "timeline_events": [t.to_dict() for t in self.timeline_events],
            "state_transitions": {k: v.to_dict() for k, v in self.state_transitions.items()},
            "causal_graph": self.causal_graph.to_dict(),
        }
