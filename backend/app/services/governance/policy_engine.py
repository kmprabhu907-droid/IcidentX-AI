"""
INCIDENTX AI - Enterprise Governance Policy Engine
Evaluates AI agent permissions, approval requirements, data retention policies,
and organizational thresholds deterministically.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.governance import GovernancePolicy

DEFAULT_POLICIES = {
    "AI_EXECUTION_PERMISSION": {
        "allowed_autonomous_actions": ["scale_service", "restart_pod", "clear_cache"],
        "max_autonomous_risk_score": 0.40,
        "max_daily_autonomous_executions": 25,
        "require_human_gate_for_destructive": True,
    },
    "APPROVAL_POLICY": {
        "require_dual_approval": False,
        "dual_approval_risk_threshold": 0.70,
        "allowed_approver_roles": ["SUPER_ADMIN", "ORGANIZATION_ADMIN", "SRE_ENGINEER"],
    },
    "DATA_RETENTION": {
        "retention_days": 90,
        "archive_before_purge": True,
        "immutable_audit_years": 7,
    },
    "ORG_LIMITS": {
        "max_concurrent_simulations": 5,
        "max_monthly_incidents": 500,
        "max_registered_users": 50,
    },
}


class GovernancePolicyEngine:
    """Deterministic governance evaluation engine for enterprise reliability operations."""

    @staticmethod
    async def get_policy(
        session: AsyncSession,
        organization_id: str,
        policy_type: str
    ) -> Dict[str, Any]:
        """
        Retrieves active policy rules, falling back to enterprise security defaults.
        """
        query = select(GovernancePolicy).where(
            GovernancePolicy.organization_id == organization_id,
            GovernancePolicy.policy_type == policy_type,
            GovernancePolicy.is_enforced == True
        )
        result = await session.execute(query)
        policy = result.scalar_one_or_none()

        if policy and policy.rules:
            try:
                return json.loads(policy.rules)
            except Exception:
                pass

        return DEFAULT_POLICIES.get(policy_type, {})

    @classmethod
    async def evaluate_ai_remediation_permission(
        cls,
        session: AsyncSession,
        organization_id: str,
        action_type: str,
        risk_score: float
    ) -> Tuple[bool, str]:
        """
        Determines whether an AI agent can autonomously trigger a remediation action
        or whether human approval is mandatory.
        """
        rules = await cls.get_policy(session, organization_id, "AI_EXECUTION_PERMISSION")
        allowed_actions = rules.get("allowed_autonomous_actions", ["scale_service", "restart_pod"])
        max_risk = rules.get("max_autonomous_risk_score", 0.40)
        require_gate = rules.get("require_human_gate_for_destructive", True)

        # Highly destructive actions always require human gate
        destructive_actions = {"delete_database", "truncate_tables", "drop_schema", "rollback_firmware"}
        if action_type in destructive_actions and require_gate:
            return False, f"Destructive action '{action_type}' strictly mandates human-in-the-loop authorization"

        if action_type not in allowed_actions:
            return False, f"Action '{action_type}' is not on the autonomous execution allowlist"

        if risk_score > max_risk:
            return False, f"Risk score {risk_score:.2f} exceeds autonomous threshold {max_risk:.2f}"

        return True, "Autonomous execution permitted under active governance policy"

    @classmethod
    async def evaluate_approval_requirements(
        cls,
        session: AsyncSession,
        organization_id: str,
        risk_score: float
    ) -> Dict[str, Any]:
        """
        Determines required approvals and role authorizations based on risk score.
        """
        rules = await cls.get_policy(session, organization_id, "APPROVAL_POLICY")
        dual_threshold = rules.get("dual_approval_risk_threshold", 0.70)
        allowed_roles = rules.get("allowed_approver_roles", ["SUPER_ADMIN", "ORGANIZATION_ADMIN", "SRE_ENGINEER"])

        needs_dual = rules.get("require_dual_approval", False) or (risk_score >= dual_threshold)

        return {
            "required_approvals": 2 if needs_dual else 1,
            "dual_approval_mandated": needs_dual,
            "risk_score": risk_score,
            "allowed_roles": allowed_roles,
            "policy_reason": "High-risk remediation mandates dual-engineer signoff" if needs_dual else "Standard single approval sufficient",
        }

    @classmethod
    async def get_retention_days(
        cls,
        session: AsyncSession,
        organization_id: str
    ) -> int:
        """
        Retrieves active data retention window in days.
        """
        rules = await cls.get_policy(session, organization_id, "DATA_RETENTION")
        return int(rules.get("retention_days", 90))
