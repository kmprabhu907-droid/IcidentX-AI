"""
INCIDENTX AI - Historical Remediation Learner
Learns from past remediation successes, failures, and rollbacks.
Ensures the system never assumes an action will automatically succeed without empirical proof.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.remediation import RemediationAction
from backend.app.models.reliability import RegressionRecord
from backend.app.services.reliability_memory.models import RemediationLearningSummary


# Documented known side-effect patterns from SRE domain knowledge
SIDE_EFFECT_REGISTRY: Dict[str, List[str]] = {
    "act-clear-cache": [
        "Inbound cache stampede on database",
        "Elevated read latencies for 60 seconds during cold cache warm-up",
    ],
    "act-restart-service": [
        "Temporary in-flight HTTP 502/503 dropped requests during process boot",
        "Database reconnection burst upon startup",
    ],
    "act-scale-replicas": [
        "Increased total database connection pool demand across additional pods",
        "Pod scheduling latency under CPU cluster congestion",
    ],
    "act-reset-db-pool": [
        "Active long-running transaction rollback",
        "Brief client connection reconnect latency",
    ],
    "act-apply-rate-limit": [
        "Legitimate client 429 Too Many Requests drops",
    ],
}


class RemediationLearner:
    """
    Analyzes all historical executions of remediation strategies to derive empirical reliability advice.
    """

    @classmethod
    async def get_action_learning(
        cls,
        action_id: str,
        db: AsyncSession,
        target_service: Optional[str] = None,
    ) -> RemediationLearningSummary:
        """
        Synthesizes historical learning for a specific remediation action ID.
        """
        query = select(RemediationAction).where(RemediationAction.action_id == action_id)
        if target_service:
            query = query.where(RemediationAction.target_service_name == target_service)
        query = query.order_by(desc(RemediationAction.created_at)).limit(100)

        result = await db.execute(query)
        actions = result.scalars().all()

        total = len(actions)
        if total == 0:
            return RemediationLearningSummary(
                action_id=action_id,
                action_name=action_id,
                target_service=target_service or "all",
                total_executions=0,
                success_rate=0.0,
                sustained_success_count=0,
                temporary_success_count=0,
                failed_count=0,
                rollback_count=0,
                recurrence_count=0,
                known_side_effects=SIDE_EFFECT_REGISTRY.get(action_id, []),
                reusable_advice="No prior execution history recorded. Execute under HUMAN_APPROVAL mode.",
            )

        action_name = actions[0].name
        target_svc = target_service or actions[0].target_service_name

        verified = 0
        failed = 0
        rollbacks = 0

        for a in actions:
            if a.status == "FAILED" or a.verification_status == "FAILED":
                failed += 1
            elif a.verification_status == "VERIFIED":
                verified += 1

            if a.rollback_status in ["EXECUTING", "ROLLED_BACK", "ROLLBACK_FAILED"]:
                rollbacks += 1

        # Check how many regression records reference this action or target service
        regr_q = (
            select(RegressionRecord)
            .where(
                RegressionRecord.service_name == target_svc,
                RegressionRecord.status.in_(["ACTIVE", "CONFIRMED"]),
            )
        )
        regr_r = await db.execute(regr_q)
        regressions = regr_r.scalars().all()
        recurrences = len(regressions)

        sustained = max(0, verified - recurrences)
        temporary = min(verified, recurrences)
        success_rate = (sustained / total) if total > 0 else 0.0

        # Formulate actionable advice
        side_effects = SIDE_EFFECT_REGISTRY.get(action_id, [])
        if rollbacks > 0:
            advice = (
                f"Action '{action_id}' required rollback in {rollbacks} previous execution(s). "
                f"Ensure strict canary verification before execution."
            )
        elif temporary > sustained:
            advice = (
                f"Action '{action_id}' frequently provides only temporary recovery ({temporary} temporary vs {sustained} sustained). "
                f"Address root cause infrastructure limits rather than repeating standalone."
            )
        elif success_rate >= 0.75:
            advice = (
                f"Action '{action_id}' has a {int(success_rate * 100)}% sustained success rate. "
                f"Recommended for execution subject to standard policy checks."
            )
        else:
            advice = (
                f"Moderate success rate ({int(success_rate * 100)}%). Verify telemetry stability for 15 minutes post-execution."
            )

        return RemediationLearningSummary(
            action_id=action_id,
            action_name=action_name,
            target_service=target_svc,
            total_executions=total,
            success_rate=success_rate,
            sustained_success_count=sustained,
            temporary_success_count=temporary,
            failed_count=failed,
            rollback_count=rollbacks,
            recurrence_count=recurrences,
            known_side_effects=side_effects,
            reusable_advice=advice,
        )

    @classmethod
    async def get_all_remediation_learnings(
        cls,
        db: AsyncSession,
    ) -> List[RemediationLearningSummary]:
        """Returns learning summaries for all known remediation action IDs."""
        action_ids = [
            "act-reset-db-pool",
            "act-restart-service",
            "act-scale-replicas",
            "act-clear-cache",
            "act-apply-rate-limit",
            "act-toggle-feature-flag",
            "act-switch-dependency",
        ]
        learnings: List[RemediationLearningSummary] = []
        for aid in action_ids:
            summary = await cls.get_action_learning(aid, db)
            if summary.total_executions > 0:
                learnings.append(summary)
        return learnings
