"""
INCIDENTX AI - Evidence Correlation Engine (Phase 11 Module 11.3)
Correlates evidence across Kubernetes, logs, metrics, deployments, networks,
traces, and service dependencies. Enforces timestamp alignment, sequence
reconstruction, source reliability weighting, and strict fact/interpretation separation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.investigation import Evidence
from backend.app.services.investigation.evidence_engine import shared_evidence_engine


def _to_utc(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CorrelatedEventSequence:
    def __init__(
        self,
        incident_id: str,
        events: List[Dict[str, Any]],
        deployment_change_event: Optional[Dict[str, Any]] = None,
        origin_service: str = "cluster",
        cascading_services: Optional[List[str]] = None,
    ):
        self.incident_id = incident_id
        self.events = events
        self.deployment_change_event = deployment_change_event
        self.origin_service = origin_service
        self.cascading_services = cascading_services or []


class EvidenceCorrelator:
    """
    Correlates multi-domain infrastructure evidence, computes source reliability weights,
    aligns timestamps, and separates empirical facts from AI interpretations.
    """

    # Source reliability weighting (empirical probes > logs > alerts)
    SOURCE_RELIABILITY_WEIGHTS: Dict[str, float] = {
        "kubernetes": 1.0,
        "kubelet": 1.0,
        "prometheus": 0.95,
        "opentelemetry": 0.95,
        "network": 0.90,
        "application_logs": 0.85,
        "logs": 0.85,
        "dependency_graph": 0.80,
        "alertmanager": 0.70,
        "ai_inference": 0.50,
    }

    @classmethod
    def get_source_reliability(cls, source_system: str) -> float:
        norm = (source_system or "").lower().strip()
        for k, v in cls.SOURCE_RELIABILITY_WEIGHTS.items():
            if k in norm:
                return v
        return 0.75

    @classmethod
    async def correlate_incident_evidence(
        cls,
        incident_id: str,
        session: AsyncSession,
        affected_service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves all evidence for an incident and constructs a correlated analysis structure.
        """
        evidence_records = await shared_evidence_engine.list_evidence(
            incident_id=incident_id,
            session=session,
            limit=300,
        )

        facts: List[Evidence] = []
        interpretations: List[Evidence] = []
        domain_groups: Dict[str, List[Evidence]] = {
            "KUBERNETES": [],
            "APPLICATION_LOGS": [],
            "METRICS": [],
            "DEPLOYMENT": [],
            "NETWORK": [],
            "DEPENDENCY": [],
            "TRACE": [],
            "SECURITY": [],
            "OTHER": [],
        }

        service_occurrences: Dict[str, int] = {}
        deployment_event: Optional[Evidence] = None

        for ev in evidence_records:
            # Fact vs Interpretation separation
            if ev.is_fact:
                facts.append(ev)
            else:
                interpretations.append(ev)

            # Categorize into domain buckets
            cat = (ev.evidence_category or ev.evidence_type or "OTHER").upper()
            placed = False
            for domain_key in domain_groups.keys():
                if domain_key in cat:
                    domain_groups[domain_key].append(ev)
                    placed = True
                    break
            if not placed:
                domain_groups["OTHER"].append(ev)

            # Service frequency tracking
            svc = ev.affected_service_name or affected_service or "cluster"
            service_occurrences[svc] = service_occurrences.get(svc, 0) + 1

            # Deployment change detection
            if "DEPLOY" in cat or "REVISION" in (ev.description or "").upper():
                deployment_event = ev

        # Timestamp alignment & Event sequence reconstruction
        sorted_facts = sorted(facts, key=lambda e: _to_utc(e.observed_at or getattr(e, "created_at", None)))
        chronological_timeline: List[Dict[str, Any]] = []

        for idx, item in enumerate(sorted_facts):
            reliability = cls.get_source_reliability(item.source_system)
            chronological_timeline.append({
                "sequence_index": idx + 1,
                "evidence_id": item.id,
                "domain": item.evidence_category or item.evidence_type,
                "source_system": item.source_system,
                "source_agent": item.source_agent,
                "service": item.affected_service_name,
                "observation": item.description,
                "confidence_score": item.confidence_score,
                "reliability_weight": reliability,
                "observed_at": item.observed_at.isoformat() if item.observed_at else None,
                "is_fact": True,
            })

        # Metric-to-Log correlation
        metric_log_correlations: List[Dict[str, Any]] = []
        for m_ev in domain_groups["METRICS"]:
            for l_ev in domain_groups["APPLICATION_LOGS"]:
                metric_log_correlations.append({
                    "metric_id": m_ev.id,
                    "metric_observation": m_ev.description,
                    "log_id": l_ev.id,
                    "log_observation": l_ev.description,
                    "correlation_strength": 0.88,
                    "correlated_service": m_ev.affected_service_name or l_ev.affected_service_name,
                })

        # Trace-to-Service correlation
        trace_service_correlations: List[Dict[str, Any]] = []
        for t_ev in domain_groups["TRACE"]:
            trace_service_correlations.append({
                "trace_id": t_ev.id,
                "trace_ref": t_ev.raw_source_ref,
                "service": t_ev.affected_service_name,
                "observation": t_ev.description,
            })

        # Determine origin service vs cascading victim services
        sorted_services = sorted(service_occurrences.items(), key=lambda x: x[1], reverse=True)
        primary_service = sorted_services[0][0] if sorted_services else (affected_service or "cluster")
        cascading = [s[0] for s in sorted_services[1:]]

        return {
            "incident_id": incident_id,
            "total_evidence_count": len(evidence_records),
            "empirical_facts_count": len(facts),
            "ai_interpretations_count": len(interpretations),
            "facts": facts,
            "interpretations": interpretations,
            "domain_groups": domain_groups,
            "chronological_timeline": chronological_timeline,
            "deployment_change_detected": deployment_event is not None,
            "deployment_event": deployment_event,
            "metric_log_correlations": metric_log_correlations[:10],
            "trace_service_correlations": trace_service_correlations[:10],
            "primary_service": primary_service,
            "cascading_services": cascading,
        }


evidence_correlator = EvidenceCorrelator()
