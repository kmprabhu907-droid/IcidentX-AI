"""
INCIDENTX AI - Controlled Self-Learning Engine (Phase 13 Module 13.6)
Learns from verified root causes, counter-evidence, human corrections, and remediation results.
Strict Safeguards: No training on unverified AI hypotheses, no permission changes,
versioned & reversible policy updates, and human approval gating.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.learning.schemas import (
    HumanFeedback,
    LearningPolicyChange,
)


class ControlledSelfLearningEngine:
    """
    Implements safe, explainable, versioned, and reversible self-learning.
    Updates agent prioritization, evidence weights, and hypothesis rankings.
    """

    MIN_CONFIDENCE_FOR_LEARNING = 0.75

    def __init__(self):
        # Versioned policy history (stack)
        self._policy_versions: Dict[str, LearningPolicyChange] = {}
        self._feedback_records: Dict[str, HumanFeedback] = {}
        self._active_version_id: Optional[str] = None
        self._initialize_base_policy()

    def get_active_policy(self) -> LearningPolicyChange:
        """Returns the currently active learning policy."""
        if self._active_version_id and self._active_version_id in self._policy_versions:
            return self._policy_versions[self._active_version_id]
        # Return fallback base policy
        return list(self._policy_versions.values())[0]

    def list_policy_versions(self) -> List[LearningPolicyChange]:
        """Lists all historical and current policy versions."""
        return sorted(self._policy_versions.values(), key=lambda v: v.created_at, reverse=True)

    def learn_from_incident(
        self,
        incident_id: str,
        verified_root_cause_category: str,
        is_verified: bool,
        confidence_score: float,
        successful_remediations: List[str],
        failed_remediations: List[str],
        human_approved: bool = False,
        approved_by: Optional[str] = None,
        rationale: str = "",
    ) -> Optional[LearningPolicyChange]:
        """
        Calculates a new versioned policy increment.
        Enforces Safeguard: Rejects unverified conclusions (< MIN_CONFIDENCE_FOR_LEARNING).
        """
        # SAFEGUARD 1: Reject unverified conclusions unless explicitly human-approved
        if not human_approved and (not is_verified or confidence_score < self.MIN_CONFIDENCE_FOR_LEARNING):
            logger.warning(
                f"[SelfLearningEngine] SAFEGUARD ACTIVATED: Refusing to learn from incident {incident_id}. "
                f"Confidence {confidence_score:.2f} < threshold {self.MIN_CONFIDENCE_FOR_LEARNING}."
            )
            return None

        current = self.get_active_policy()
        new_version_id = f"pol-v{len(self._policy_versions) + 1}-{uuid.uuid4().hex[:6]}"

        # Copy existing weights
        new_hyp_weights = dict(current.hypothesis_ranking_weights)
        new_agent_priorities = dict(current.agent_task_priorities)
        new_ev_weights = dict(current.evidence_collection_weights)

        # 1. Bias hypothesis ranking towards verified root cause categories
        cat = verified_root_cause_category.upper()
        prev_w = new_hyp_weights.get(cat, 1.0)
        # Bounded incremental learning (prevent one incident from dominating)
        increment = 0.05 if not human_approved else 0.10
        new_hyp_weights[cat] = round(min(2.0, max(0.2, prev_w + increment)), 2)

        # 2. Adjust Agent priorities based on category
        if "MEMORY" in cat or "CRASH" in cat:
            new_agent_priorities["KubernetesInvestigatorAgent"] = min(10, new_agent_priorities.get("KubernetesInvestigatorAgent", 5) + 1)
            new_ev_weights["container_restart_logs"] = round(min(2.0, new_ev_weights.get("container_restart_logs", 1.0) + 0.05), 2)
        elif "DATABASE" in cat or "POOL" in cat:
            new_agent_priorities["DatabaseInvestigatorAgent"] = min(10, new_agent_priorities.get("DatabaseInvestigatorAgent", 5) + 1)
            new_ev_weights["db_pool_telemetry"] = round(min(2.0, new_ev_weights.get("db_pool_telemetry", 1.0) + 0.05), 2)
        elif "LATENCY" in cat or "NETWORK" in cat:
            new_agent_priorities["MetricsInvestigatorAgent"] = min(10, new_agent_priorities.get("MetricsInvestigatorAgent", 5) + 1)
            new_ev_weights["p95_latency_traces"] = round(min(2.0, new_ev_weights.get("p95_latency_traces", 1.0) + 0.05), 2)

        default_rationale = (
            f"Incremented weights for category '{cat}' following verified incident {incident_id}. "
            f"Validated by empirical recovery and {len(successful_remediations)} effective remediation(s)."
        )

        new_policy = LearningPolicyChange(
            version_id=new_version_id,
            created_at=datetime.now(timezone.utc),
            source_incident_ids=[incident_id],
            hypothesis_ranking_weights=new_hyp_weights,
            agent_task_priorities=new_agent_priorities,
            evidence_collection_weights=new_ev_weights,
            rationale=rationale or default_rationale,
            human_approved=human_approved,
            approved_by=approved_by,
            is_active=True,
            previous_version_id=current.version_id,
        )

        # Deactivate old version and set new active
        current.is_active = False
        self._policy_versions[current.version_id] = current
        self._policy_versions[new_version_id] = new_policy
        self._active_version_id = new_version_id

        logger.info(f"[SelfLearningEngine] Landed versioned policy {new_version_id} (active).")
        return new_policy

    def rollback_to_version(self, target_version_id: str, rolled_back_by: str = "oncall-engineer") -> bool:
        """
        SAFEGUARD: Instantly rolls back to any historical version.
        """
        if target_version_id not in self._policy_versions:
            logger.error(f"[SelfLearningEngine] Target version {target_version_id} not found.")
            return False

        current = self.get_active_policy()
        current.is_active = False
        self._policy_versions[current.version_id] = current

        target = self._policy_versions[target_version_id]
        target.is_active = True
        self._active_version_id = target_version_id
        logger.info(f"[SelfLearningEngine] Successfully rolled back to policy {target_version_id} by {rolled_back_by}.")
        return True

    def record_human_feedback(self, feedback: HumanFeedback) -> None:
        """Records on-call engineer human feedback."""
        self._feedback_records[feedback.feedback_id] = feedback
        logger.info(f"[SelfLearningEngine] Recorded human feedback for incident {feedback.incident_id} (Rating: {feedback.rating}/5)")

        # If human corrected root cause or approved update, learn with human gating
        if feedback.approved_learning_update and feedback.corrected_root_cause:
            self.learn_from_incident(
                incident_id=feedback.incident_id,
                verified_root_cause_category=feedback.corrected_root_cause,
                is_verified=True,
                confidence_score=1.0,
                successful_remediations=[],
                failed_remediations=[],
                human_approved=True,
                approved_by=feedback.reviewer,
                rationale=f"Human SRE correction: {feedback.comments}",
            )

    def list_feedback(self, incident_id: Optional[str] = None) -> List[HumanFeedback]:
        """Lists human feedback entries."""
        if incident_id:
            return [f for f in self._feedback_records.values() if f.incident_id == incident_id]
        return list(self._feedback_records.values())

    def _initialize_base_policy(self) -> None:
        """Initial baseline policy v1."""
        v1 = LearningPolicyChange(
            version_id="pol-v1-base",
            created_at=datetime.now(timezone.utc),
            source_incident_ids=[],
            hypothesis_ranking_weights={
                "MEMORY_LEAK": 1.0,
                "DATABASE_EXHAUSTION": 1.0,
                "CONCURRENCY_DEADLOCK": 1.0,
                "CONFIG_MISMATCH": 1.0,
                "NETWORK_SATURATION": 1.0,
                "UPSTREAM_OUTAGE": 1.0,
            },
            agent_task_priorities={
                "KubernetesInvestigatorAgent": 5,
                "MetricsInvestigatorAgent": 5,
                "LogIntelligenceAgent": 5,
                "DatabaseInvestigatorAgent": 4,
                "SecurityInvestigatorAgent": 3,
            },
            evidence_collection_weights={
                "pod_crash_logs": 1.0,
                "http_error_spikes": 1.0,
                "container_restart_logs": 1.0,
                "db_pool_telemetry": 1.0,
                "p95_latency_traces": 1.0,
            },
            rationale="Baseline initial learning configuration.",
            human_approved=True,
            approved_by="SYSTEM_ARCHITECT",
            is_active=True,
            previous_version_id=None,
        )
        self._policy_versions[v1.version_id] = v1
        self._active_version_id = v1.version_id


self_learning_engine = ControlledSelfLearningEngine()
