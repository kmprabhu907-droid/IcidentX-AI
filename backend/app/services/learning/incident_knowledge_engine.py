"""
INCIDENTX AI - Incident Knowledge Engine (Phase 13 Module 13.5)
Searchable historical incident knowledge store.
Performs similarity scoring, recurring pattern identification, and effective remediation discovery.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import re
import uuid

from backend.app.core.logging import logger
from backend.app.services.learning.schemas import (
    FailurePattern,
    IncidentKnowledgeEntry,
    SimilarIncidentMatch,
)


class IncidentKnowledgeEngine:
    """
    Searchable, multi-feature historical incident knowledge store.
    Identifies recurring failure patterns and retrieves previous effective remediations.
    """

    def __init__(self):
        # In-memory knowledge store (persists across runtime, can be seeded or loaded from DB)
        self._entries: Dict[str, IncidentKnowledgeEntry] = {}
        self._seed_default_knowledge()

    def store_incident(self, entry: IncidentKnowledgeEntry) -> None:
        """Stores or updates an incident knowledge entry."""
        self._entries[entry.incident_id] = entry
        logger.info(f"[IncidentKnowledgeEngine] Stored incident entry: {entry.incident_id} ({entry.title})")

    def get_incident(self, incident_id: str) -> Optional[IncidentKnowledgeEntry]:
        """Retrieves a single entry by incident ID."""
        return self._entries.get(incident_id)

    def list_all(self) -> List[IncidentKnowledgeEntry]:
        """Lists all stored knowledge entries."""
        return list(self._entries.values())

    def search_similar(
        self,
        service_name: Optional[str] = None,
        error_signature: Optional[str] = None,
        query_text: Optional[str] = None,
        min_similarity: float = 0.30,
        limit: int = 5,
    ) -> List[SimilarIncidentMatch]:
        """
        Finds similar historical incidents using weighted multi-feature matching:
        - Common service matching (weight 0.35)
        - Error signature matching (weight 0.35)
        - Text / keyword overlap in title and root cause (weight 0.30)
        """
        matches: List[SimilarIncidentMatch] = []
        q_tokens = set(re.findall(r"\w+", query_text.lower())) if query_text else set()
        err_tokens = set(re.findall(r"\w+", error_signature.lower())) if error_signature else set()

        for inc in self._entries.values():
            score = 0.0
            matched_features: List[str] = []
            common_services: List[str] = []

            # 1. Service Match
            if service_name and service_name in inc.affected_services:
                score += 0.35
                common_services.append(service_name)
                matched_features.append(f"Affected Service: {service_name}")

            # 2. Error Signature Match (Jaccard)
            if err_tokens:
                inc_err_tokens = set(re.findall(r"\w+", inc.error_signature.lower()))
                if inc_err_tokens:
                    jaccard = len(err_tokens.intersection(inc_err_tokens)) / len(err_tokens.union(inc_err_tokens))
                    if jaccard > 0.2:
                        score += 0.35 * jaccard
                        matched_features.append(f"Matching Error Signature ({jaccard*100:.0f}% overlap)")

            # 3. Query Text / Root Cause Overlap
            if q_tokens:
                inc_text = f"{inc.title} {inc.verified_root_cause}".lower()
                inc_tokens = set(re.findall(r"\w+", inc_text))
                if inc_tokens:
                    text_jaccard = len(q_tokens.intersection(inc_tokens)) / len(q_tokens.union(inc_tokens))
                    if text_jaccard > 0.1:
                        score += 0.30 * text_jaccard
                        matched_features.append("Root Cause / Title Keywords")

            score = min(1.0, round(score, 2))

            if score >= min_similarity:
                matches.append(
                    SimilarIncidentMatch(
                        incident_id=inc.incident_id,
                        title=inc.title,
                        severity=inc.severity,
                        similarity_score=score,
                        matching_features=matched_features,
                        common_services=common_services or inc.affected_services,
                        verified_root_cause=inc.verified_root_cause,
                        recommended_remediations=inc.effective_remediations,
                        postmortem_id=inc.postmortem_id,
                    )
                )

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:limit]

    def detect_recurring_patterns(self, min_occurrences: int = 2) -> List[FailurePattern]:
        """
        Groups incidents by service + root cause category to detect systemic failure patterns.
        """
        groups: Dict[str, List[IncidentKnowledgeEntry]] = {}
        for entry in self._entries.values():
            key = f"{','.join(sorted(entry.affected_services))}:{entry.root_cause_category}"
            if key not in groups:
                groups[key] = []
            groups[key].append(entry)

        patterns: List[FailurePattern] = []
        for key, incidents in groups.items():
            if len(incidents) >= min_occurrences:
                sample = incidents[0]
                pat_id = f"pat-{uuid.uuid4().hex[:8]}"
                patterns.append(
                    FailurePattern(
                        pattern_id=pat_id,
                        pattern_name=f"Recurring {sample.root_cause_category} on {', '.join(sample.affected_services)}",
                        frequency_count=len(incidents),
                        affected_services=sample.affected_services,
                        common_root_cause=sample.verified_root_cause,
                        error_signature=sample.error_signature,
                        mean_time_to_detect_minutes=5.2,
                        mean_time_to_recover_minutes=8.4,
                        recommended_systemic_fix=(
                            f"Implement automated circuit breakers or proactive horizontal pod autoscaling "
                            f"on {', '.join(sample.affected_services)} to prevent recurrent {sample.root_cause_category} outages."
                        ),
                        detected_at=datetime.now(timezone.utc),
                    )
                )

        return patterns

    def _seed_default_knowledge(self) -> None:
        """Seeds initial historical knowledge base for realistic incident retrieval."""
        seeds = [
            IncidentKnowledgeEntry(
                incident_id="INC-HIST-101",
                title="Payment Service Memory Leak and OOMKilled Cascades",
                severity="SEV-1",
                affected_services=["payment-service"],
                environment="PRODUCTION",
                incident_fingerprint="fp-payment-oom-v1",
                error_signature="java.lang.OutOfMemoryError: Java heap space",
                root_cause_category="MEMORY_LEAK",
                verified_root_cause="Unbounded in-memory ledger transaction cache caused heap exhaustion and OOMKilled pod evictions.",
                deployment_sha="git-sha-7a8f12",
                key_metrics_impacted=["memory_percent", "pod_restart_count", "http_5xx_error_rate"],
                effective_remediations=["k8s-rollback-deployment", "k8s-restart-deployment"],
                failed_remediations=["k8s-scale-deployment"],
                recovery_status="RECOVERY_SUCCESSFUL",
                is_verified_by_human=True,
                learning_weight=1.0,
            ),
            IncidentKnowledgeEntry(
                incident_id="INC-HIST-102",
                title="Order Service Database Connection Pool Starvation",
                severity="SEV-2",
                affected_services=["order-service"],
                environment="PRODUCTION",
                incident_fingerprint="fp-order-db-pool",
                error_signature="ConnectionPoolTimeoutException: Timeout waiting for idle connection",
                root_cause_category="DATABASE_EXHAUSTION",
                verified_root_cause="Slow unindexed analytical query locked connection pool slots, blocking API request threads.",
                deployment_sha="git-sha-3c99e1",
                key_metrics_impacted=["db_query_latency_ms", "p95_latency_ms", "http_5xx_error_rate"],
                effective_remediations=["app-trigger-recovery-workflow", "k8s-restart-deployment"],
                failed_remediations=[],
                recovery_status="RECOVERY_SUCCESSFUL",
                is_verified_by_human=True,
                learning_weight=1.0,
            ),
            IncidentKnowledgeEntry(
                incident_id="INC-HIST-103",
                title="Auth Service Token Verification Deadlock",
                severity="SEV-1",
                affected_services=["auth-service"],
                environment="PRODUCTION",
                incident_fingerprint="fp-auth-deadlock",
                error_signature="ThreadDeadlockException: synchronized lock order inversion",
                root_cause_category="CONCURRENCY_DEADLOCK",
                verified_root_cause="Contention on shared JWT cryptographic key cache during high concurrent login spikes.",
                deployment_sha="git-sha-9b21f0",
                key_metrics_impacted=["p95_latency_ms", "p99_latency_ms", "pod_readiness_ratio"],
                effective_remediations=["k8s-restart-deployment", "k8s-scale-deployment"],
                failed_remediations=[],
                recovery_status="RECOVERY_SUCCESSFUL",
                is_verified_by_human=True,
                learning_weight=1.0,
            ),
        ]
        for s in seeds:
            self._entries[s.incident_id] = s


incident_knowledge_engine = IncidentKnowledgeEngine()
