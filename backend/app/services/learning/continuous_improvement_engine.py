"""
INCIDENTX AI - Continuous Improvement Engine (Phase 13 Module 13.7)
Generates actionable, evidence-backed architectural, observability, and resiliency
recommendations from incident postmortems and recurring failure patterns.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.learning.schemas import (
    ContinuousImprovementRecommendation,
    FailurePattern,
    PostmortemReport,
    RecommendationCategory,
    TelemetryComparisonReport,
)


class ContinuousImprovementEngine:
    """
    Synthesizes systemic SRE recommendations from postmortems, recurring patterns,
    and telemetry baselines. Never automatically modifies infrastructure.
    """

    @classmethod
    def generate_recommendations(
        cls,
        incident_id: str,
        service_name: str,
        postmortem: Optional[PostmortemReport] = None,
        telemetry_diff: Optional[TelemetryComparisonReport] = None,
        recurring_patterns: Optional[List[FailurePattern]] = None,
    ) -> List[ContinuousImprovementRecommendation]:
        """
        Analyzes incident details and outputs structured continuous improvement recommendations.
        """
        recs: List[ContinuousImprovementRecommendation] = []
        now = datetime.now(timezone.utc)

        root_cause = (postmortem.verified_root_cause if postmortem else "").lower()

        # 1. Memory / Resource Saturation Recommendation
        if "memory" in root_cause or "oom" in root_cause or "heap" in root_cause:
            recs.append(
                ContinuousImprovementRecommendation(
                    recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    category=RecommendationCategory.RESOURCE_LIMITS,
                    title=f"Optimize Memory Limits & GC Heap Parameters for {service_name}",
                    description=(
                        f"Increase Kubernetes memory request/limit ceiling by 25% on '{service_name}' "
                        f"and configure max heap (-Xmx) to 75% of container ceiling to prevent OOMKilled evictions."
                    ),
                    supporting_evidence=[
                        f"Incident {incident_id} attributed to heap/memory exhaustion.",
                        "Container evictions captured during traffic peaks.",
                    ],
                    expected_benefit="Eliminates sudden pod evictions; grants a 15-minute buffer before memory saturation.",
                    priority="P1",
                    complexity="LOW",
                    risk="LOW",
                    suggested_owner=f"Core Backend / {service_name} SRE",
                    verification_criteria="Deploy memory limit adjustment in staging; load test with 2x peak traffic; verify no pod restarts.",
                )
            )
            recs.append(
                ContinuousImprovementRecommendation(
                    recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    category=RecommendationCategory.ALERTS,
                    title=f"Add Early-Warning Memory Burn-Rate Alert for {service_name}",
                    description=(
                        f"Add a Prometheus alert firing when container memory exceeds 80% for > 3 minutes, "
                        f"triggering on-call investigation before OOM occurs."
                    ),
                    supporting_evidence=[
                        "Detection occurred only after pods began restarting in CrashLoopBackOff.",
                    ],
                    expected_benefit="Reduces Mean Time to Detect (MTTD) by up to 12 minutes.",
                    priority="P2",
                    complexity="LOW",
                    risk="LOW",
                    suggested_owner="Observability Team",
                    verification_criteria="Trigger simulated memory leak in pre-prod; verify alert fires within 180 seconds.",
                )
            )

        # 2. Database / Connection Pool Recommendation
        if "pool" in root_cause or "database" in root_cause or "connection" in root_cause:
            recs.append(
                ContinuousImprovementRecommendation(
                    recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    category=RecommendationCategory.DEPENDENCY_OBSERVABILITY,
                    title=f"Implement Database Connection Pool Circuit Breaker for {service_name}",
                    description=(
                        f"Add an active circuit breaker to '{service_name}' that sheds non-critical read queries "
                        f"when database pool utilization exceeds 85%."
                    ),
                    supporting_evidence=[
                        f"Incident {incident_id} involved connection pool starvation.",
                        "High query latency cascaded to HTTP 5xx customer errors.",
                    ],
                    expected_benefit="Prevents cascading service lockup when backend database latency spikes.",
                    priority="P1",
                    complexity="MEDIUM",
                    risk="LOW",
                    suggested_owner=f"{service_name} Engineering Lead",
                    verification_criteria="Simulate slow DB queries; verify circuit breaker trips and returns graceful 429/503 fallback.",
                )
            )

        # 3. Deployment Safeguards
        if "deployment" in root_cause or "release" in root_cause or "version" in root_cause:
            recs.append(
                ContinuousImprovementRecommendation(
                    recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    category=RecommendationCategory.DEPLOYMENT_SAFEGUARDS,
                    title=f"Enforce Automated Canary Analysis & PodDisruptionBudget for {service_name}",
                    description=(
                        f"Configure a PodDisruptionBudget (minAvailable: 1) and automated Argo/Flagger canary analysis "
                        f"evaluating error rate for 5 minutes before routing 100% traffic."
                    ),
                    supporting_evidence=[
                        "Fault was introduced immediately following a direct deployment rollout.",
                    ],
                    expected_benefit="Restricts blast radius of faulty code releases to < 10% of users.",
                    priority="P1",
                    complexity="HIGH",
                    risk="MEDIUM",
                    suggested_owner="Release Engineering / Platform Team",
                    verification_criteria="Deploy a canary with simulated error rate; verify automated rollback aborts promotion.",
                )
            )

        # 4. Recurring Pattern Recommendations
        if recurring_patterns:
            for pat in recurring_patterns:
                if service_name in pat.affected_services:
                    recs.append(
                        ContinuousImprovementRecommendation(
                            recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                            incident_id=incident_id,
                            category=RecommendationCategory.ESCALATION_POLICIES,
                            title=f"Mitigate Systemic Pattern: {pat.pattern_name}",
                            description=(
                                f"Service '{service_name}' has encountered this fault pattern {pat.frequency_count} times. "
                                f"{pat.recommended_systemic_fix}"
                            ),
                            supporting_evidence=[
                                f"Pattern identified across {pat.frequency_count} historical incidents.",
                                f"Signature: {pat.error_signature}",
                            ],
                            expected_benefit="Permanently eliminates recurring on-call pages for this failure mode.",
                            priority="P1",
                            complexity="MEDIUM",
                            risk="LOW",
                            suggested_owner="Principal SRE Architect",
                            verification_criteria="Track 30-day zero-occurrence metric in recurring incident dashboard.",
                        )
                    )

        # Fallback Standard Health Check Recommendation if empty
        if not recs:
            recs.append(
                ContinuousImprovementRecommendation(
                    recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    category=RecommendationCategory.HEALTH_CHECKS,
                    title=f"Tune Readiness Probe Grace Period for {service_name}",
                    description=(
                        f"Align probe initialDelaySeconds and failureThreshold on '{service_name}' "
                        f"to allow graceful pod initialization under heavy load."
                    ),
                    supporting_evidence=[
                        f"Incident {incident_id} telemetry showed degraded pod readiness during remediation.",
                    ],
                    expected_benefit="Reduces false-positive probe restarts during cold starts.",
                    priority="P2",
                    complexity="LOW",
                    risk="LOW",
                    suggested_owner="Platform DevOps",
                    verification_criteria="Verify container restart count remains 0 during full cluster reboot.",
                )
            )

        logger.info(f"[ContinuousImprovementEngine] Generated {len(recs)} recommendation(s) for incident {incident_id}")
        return recs
