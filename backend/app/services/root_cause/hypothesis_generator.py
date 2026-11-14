"""
INCIDENTX AI - Intelligent Hypothesis Generation Engine (Phase 11 Module 11.1)
Generates multiple competing hypotheses across infrastructure domains:
Kubernetes, logs, metrics, deployments, network, dependencies, traces, security.
Every hypothesis is uniquely identified, fully attributed, and assigned an initial status.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.root_cause.schemas import (
    ConfidenceCategory,
    HypothesisItem,
    HypothesisStatus,
)


class HypothesisGenerator:
    """
    Intelligent Generator of Competing Causal Hypotheses.
    Synthesizes empirical signals from all 8 diagnostic planes into concrete, falsifiable hypotheses.
    """

    @classmethod
    def generate_hypotheses(
        cls,
        incident_id: str,
        investigation_id: Optional[str],
        correlated_data: Dict[str, Any],
        affected_service: Optional[str] = None,
    ) -> List[HypothesisItem]:
        """
        Generates competing hypotheses based on correlated multi-domain evidence.
        """
        target_service = affected_service or correlated_data.get("primary_service", "cluster")
        domain_groups = correlated_data.get("domain_groups", {})
        deployment_event = correlated_data.get("deployment_event")
        k8s_facts = domain_groups.get("KUBERNETES", [])
        log_facts = domain_groups.get("APPLICATION_LOGS", [])
        metric_facts = domain_groups.get("METRICS", [])
        deploy_facts = domain_groups.get("DEPLOYMENT", [])
        net_facts = domain_groups.get("NETWORK", [])
        trace_facts = domain_groups.get("TRACE", [])
        sec_facts = domain_groups.get("SECURITY", [])

        hypotheses: List[HypothesisItem] = []

        # ====================================================================
        # Hypothesis 1: Deployment & Code Regression
        # ====================================================================
        dep_supp = [e.id for e in deploy_facts] + [e.id for e in log_facts if "error" in (e.description or "").lower()]
        dep_trigger = (
            deployment_event.description if deployment_event
            else f"Recent container image rollout on '{target_service}'"
        )
        hypotheses.append(
            HypothesisItem(
                id=f"hyp-deploy-{uuid.uuid4().hex[:8]}",
                incident_id=incident_id,
                investigation_id=investigation_id,
                title=f"Deployment Regression on {target_service}",
                description=(
                    f"A recent deployment rollout on service '{target_service}' introduced an unhandled "
                    f"runtime exception or memory regression leading to cascade service degradation."
                ),
                affected_service=target_service,
                triggering_event=dep_trigger,
                supporting_evidence_ids=dep_supp,
                contradicting_evidence_ids=[],
                missing_evidence=[
                    "Git diff showing commit delta between image tags",
                    "Application profiling / flamegraph during error onset",
                ] if not deploy_facts else [],
                assumptions=[
                    "The deployment timestamp preceded the observed error spike",
                    "The error rate increased without a proportional traffic surge",
                ],
                source_domains=["DEPLOYMENT", "APPLICATION_LOGS"],
                confidence_score=0.75 if deploy_facts else 0.40,
                confidence_category=ConfidenceCategory.HIGH if deploy_facts else ConfidenceCategory.LOW,
                status=HypothesisStatus.SUPPORTED if deploy_facts else HypothesisStatus.PROPOSED,
                causal_chain_summary=(
                    f"Deployment Rollout -> Application Exception Spike -> Error Rate Breach on {target_service}"
                ),
            )
        )

        # ====================================================================
        # Hypothesis 2: Resource Exhaustion / Container Saturation
        # ====================================================================
        res_supp = [e.id for e in k8s_facts] + [e.id for e in metric_facts if "memory" in (e.description or "").lower() or "cpu" in (e.description or "").lower()]
        hypotheses.append(
            HypothesisItem(
                id=f"hyp-resource-{uuid.uuid4().hex[:8]}",
                incident_id=incident_id,
                investigation_id=investigation_id,
                title=f"Infrastructure Resource Exhaustion on {target_service}",
                description=(
                    f"Container or host memory/CPU saturation on '{target_service}' triggered thread pool "
                    f"exhaustion, high latency, or container OOMKilled restarts."
                ),
                affected_service=target_service,
                triggering_event=f"Memory/CPU threshold breach observed on '{target_service}' pods",
                supporting_evidence_ids=res_supp,
                contradicting_evidence_ids=[],
                missing_evidence=[
                    "JVM / Runtime heap memory dumps",
                    "Node kernel dmesg out-of-memory logs",
                ] if not k8s_facts else [],
                assumptions=[
                    "Pod restarts were directly caused by memory limit enforcement (cgroup OOM)",
                ],
                source_domains=["KUBERNETES", "METRICS"],
                confidence_score=0.82 if (k8s_facts or metric_facts) else 0.45,
                confidence_category=ConfidenceCategory.HIGH if (k8s_facts or metric_facts) else ConfidenceCategory.LOW,
                status=HypothesisStatus.SUPPORTED if (k8s_facts or metric_facts) else HypothesisStatus.PROPOSED,
                causal_chain_summary=(
                    f"Memory/CPU Surge -> Cgroup Limit Breach -> OOMKilled Restarts -> Latency Surge"
                ),
            )
        )

        # ====================================================================
        # Hypothesis 3: Database & Downstream Connection Pool Saturation
        # ====================================================================
        db_supp = [
            e.id for e in log_facts + metric_facts + trace_facts
            if any(term in (e.description or "").lower() for term in ["database", "postgres", "pool", "timeout", "sql", "connection"])
        ]
        hypotheses.append(
            HypothesisItem(
                id=f"hyp-dbpool-{uuid.uuid4().hex[:8]}",
                incident_id=incident_id,
                investigation_id=investigation_id,
                title=f"Downstream Database Connection Pool Exhaustion",
                description=(
                    f"Client connection pool to postgres-db or database worker threads saturated, "
                    f"causing request queuing and upstream gateway timeouts."
                ),
                affected_service=target_service,
                triggering_event="Exhaustion of available database client connection leases",
                supporting_evidence_ids=db_supp,
                contradicting_evidence_ids=[],
                missing_evidence=[
                    "pg_stat_activity query state breakdown",
                    "Database server-side connection metrics",
                ],
                assumptions=[
                    "Database query latency caused the client request timeout cascade",
                ],
                source_domains=["APPLICATION_LOGS", "METRICS", "TRACE"],
                confidence_score=0.68 if db_supp else 0.35,
                confidence_category=ConfidenceCategory.MODERATE if db_supp else ConfidenceCategory.LOW,
                status=HypothesisStatus.INVESTIGATING if db_supp else HypothesisStatus.PROPOSED,
                causal_chain_summary=(
                    f"DB Connection Starvation -> Request Queueing -> HTTP 504 Gateway Timeouts"
                ),
            )
        )

        # ====================================================================
        # Hypothesis 4: Network Connectivity & Socket Timeout Partition
        # ====================================================================
        net_supp = [e.id for e in net_facts] + [e.id for e in trace_facts if "timeout" in (e.description or "").lower()]
        hypotheses.append(
            HypothesisItem(
                id=f"hyp-network-{uuid.uuid4().hex[:8]}",
                incident_id=incident_id,
                investigation_id=investigation_id,
                title=f"Network Routing & Upstream Socket Timeouts",
                description=(
                    f"Inter-service network latency, packet loss, or socket timeouts between '{target_service}' "
                    f"and upstream service endpoints."
                ),
                affected_service=target_service,
                triggering_event="TCP socket connection reset or ingress timeout",
                supporting_evidence_ids=net_supp,
                contradicting_evidence_ids=[],
                missing_evidence=[
                    "CoreDNS query latency logs",
                    "Network policy ingress drop counters",
                ],
                assumptions=[
                    "Network delays occurred in transit rather than inside application code",
                ],
                source_domains=["NETWORK", "TRACE"],
                confidence_score=0.55 if net_supp else 0.30,
                confidence_category=ConfidenceCategory.MODERATE if net_supp else ConfidenceCategory.LOW,
                status=HypothesisStatus.INVESTIGATING if net_supp else HypothesisStatus.PROPOSED,
                causal_chain_summary=(
                    f"Network Transit Delay -> Socket Read Timeout -> Upstream Service Failure"
                ),
            )
        )

        return hypotheses


hypothesis_generator = HypothesisGenerator()
