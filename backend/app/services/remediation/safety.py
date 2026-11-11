"""
INCIDENTX AI - Safety & Approval Engine
Enforces execution modes (Recommendation Only, Human Approval, Controlled Autonomous),
approval gates, idempotency guarantees, execution budgets, circuit breakers, and emergency stop controls.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.models.remediation import RemediationAction, RemediationPolicy


class RemediationSecurityException(IncidentXException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=403, details=details)


class SafetyEngine:
    """
    Guards all remediation actions against unauthorized execution,
    uncontrolled autonomy, and cascading failures.
    """

    DEFAULT_MODE = "RECOMMENDATION_ONLY"
    ALLOWED_MODES = ["RECOMMENDATION_ONLY", "HUMAN_APPROVAL", "CONTROLLED_AUTONOMOUS"]

    def __init__(self):
        # In-memory circuit breaker and emergency stop state cache
        self.emergency_stop_active = False
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason: Optional[str] = None
        self._active_executions: Dict[str, str] = {}  # service_name -> action_id

    async def get_or_create_policy(self, session: AsyncSession) -> RemediationPolicy:
        """Fetch or initialize the global remediation safety policy."""
        stmt = select(RemediationPolicy).where(RemediationPolicy.name == "global-default")
        res = await session.execute(stmt)
        policy = res.scalar_one_or_none()
        if not policy:
            policy = RemediationPolicy(
                name="global-default",
                mode=self.DEFAULT_MODE,
                is_autonomous_enabled=False,
                allowlisted_action_ids='["act-clear-cache", "act-scale-replicas", "act-toggle-feature-flag", "act-apply-rate-limit", "act-restart-service"]',
                max_actions_per_incident=3,
                max_retries=1,
                cooldown_seconds=30,
                circuit_breaker_tripped=False,
                emergency_stop_active=False,
            )
            session.add(policy)
            await session.flush()
        return policy

    async def update_policy(
        self,
        session: AsyncSession,
        mode: Optional[str] = None,
        is_autonomous_enabled: Optional[bool] = None,
        allowlisted_action_ids: Optional[List[str]] = None,
        max_actions_per_incident: Optional[int] = None,
    ) -> RemediationPolicy:
        """Update safety policy settings."""
        policy = await self.get_or_create_policy(session)
        if mode:
            if mode not in self.ALLOWED_MODES:
                raise RemediationSecurityException(f"Invalid mode '{mode}'. Allowed: {self.ALLOWED_MODES}")
            policy.mode = mode
            if mode == "CONTROLLED_AUTONOMOUS":
                policy.is_autonomous_enabled = True
            elif mode == "RECOMMENDATION_ONLY":
                policy.is_autonomous_enabled = False

        if is_autonomous_enabled is not None:
            policy.is_autonomous_enabled = is_autonomous_enabled
            if not is_autonomous_enabled and policy.mode == "CONTROLLED_AUTONOMOUS":
                policy.mode = "HUMAN_APPROVAL"

        if allowlisted_action_ids is not None:
            import json
            policy.allowlisted_action_ids = json.dumps(allowlisted_action_ids)

        if max_actions_per_incident is not None:
            policy.max_actions_per_incident = max(1, min(10, max_actions_per_incident))

        await session.flush()
        logger.info(f"[SafetyEngine] Updated policy: mode={policy.mode}, autonomous={policy.is_autonomous_enabled}")
        return policy

    async def trigger_emergency_stop(self, session: AsyncSession, reason: str = "Manual emergency stop triggered.") -> RemediationPolicy:
        """Immediately trip circuit breaker and lock down all remediation execution."""
        self.emergency_stop_active = True
        self.circuit_breaker_tripped = True
        self.circuit_breaker_reason = reason

        policy = await self.get_or_create_policy(session)
        policy.emergency_stop_active = True
        policy.circuit_breaker_tripped = True
        policy.circuit_breaker_reason = reason
        policy.mode = "RECOMMENDATION_ONLY"
        policy.is_autonomous_enabled = False
        await session.flush()

        logger.critical(f"[SafetyEngine] EMERGENCY STOP ACTIVATED: {reason}")
        return policy

    async def reset_circuit_breaker(self, session: AsyncSession) -> RemediationPolicy:
        """Reset tripped circuit breaker after human verification."""
        self.emergency_stop_active = False
        self.circuit_breaker_tripped = False
        self.circuit_breaker_reason = None

        policy = await self.get_or_create_policy(session)
        policy.emergency_stop_active = False
        policy.circuit_breaker_tripped = False
        policy.circuit_breaker_reason = None
        await session.flush()

        logger.info("[SafetyEngine] Circuit breaker reset. Normal safety policy restored.")
        return policy

    async def validate_execution_safety(
        self,
        action: RemediationAction,
        session: AsyncSession,
        is_autonomous_trigger: bool = False,
    ) -> None:
        """
        Enforce comprehensive security, approval, mode, budget, and concurrency invariants.
        Raises RemediationSecurityException if any safety check fails.
        """
        # 1. Emergency Stop Check
        if self.emergency_stop_active:
            raise RemediationSecurityException(
                "Execution rejected: EMERGENCY STOP is active. All remediation is locked down."
            )

        policy = await self.get_or_create_policy(session)
        if policy.emergency_stop_active:
            self.emergency_stop_active = True
            raise RemediationSecurityException(
                "Execution rejected: Database policy indicates Emergency Stop is active."
            )

        # 2. Circuit Breaker Check
        if policy.circuit_breaker_tripped or self.circuit_breaker_tripped:
            raise RemediationSecurityException(
                f"Execution rejected: Circuit breaker is TRIPPED. Reason: {policy.circuit_breaker_reason or self.circuit_breaker_reason}. Human reset required."
            )

        # 3. Execution Mode Enforcement
        mode = policy.mode
        action.execution_mode = mode

        # MODE A: RECOMMENDATION ONLY (Default)
        if mode == "RECOMMENDATION_ONLY":
            raise RemediationSecurityException(
                "Execution rejected: Safety policy is in RECOMMENDATION_ONLY mode. Automatic and manual execution is disabled by policy."
            )

        # MODE B: HUMAN APPROVAL REQUIRED
        if mode == "HUMAN_APPROVAL":
            if action.approval_status != "APPROVED":
                raise RemediationSecurityException(
                    f"Execution rejected: Action '{action.action_id}' requires explicit human approval. Current status: '{action.approval_status}'."
                )
            if not action.approved_by:
                raise RemediationSecurityException(
                    "Execution rejected: Approval record must contain human operator identity ('approved_by')."
                )

        # MODE C: CONTROLLED AUTONOMOUS EXECUTION
        elif mode == "CONTROLLED_AUTONOMOUS":
            import json
            allowlist = []
            try:
                allowlist = json.loads(policy.allowlisted_action_ids)
            except Exception:
                allowlist = ["act-clear-cache", "act-scale-replicas"]

            # High and medium risk actions ALWAYS require human approval, even in autonomous mode!
            if action.risk_level in ["MEDIUM", "HIGH"]:
                if action.approval_status != "APPROVED":
                    raise RemediationSecurityException(
                        f"Execution rejected: Action '{action.action_id}' carries {action.risk_level} risk. High/Medium risk operations ALWAYS require human approval."
                    )
            elif is_autonomous_trigger:
                # Check allowlist for low-risk autonomous dispatch
                if action.action_id not in allowlist:
                    raise RemediationSecurityException(
                        f"Execution rejected: Action '{action.action_id}' is not in the autonomous allowlist: {allowlist}"
                    )

        # 4. Budget Enforcement (Max actions per incident)
        stmt = (
            select(RemediationAction)
            .where(
                RemediationAction.incident_id == action.incident_id,
                RemediationAction.status.in_(["EXECUTING", "EXECUTED", "VERIFIED", "FAILED"])
            )
        )
        res = await session.execute(stmt)
        executed_count = len(res.scalars().all())
        if executed_count >= policy.max_actions_per_incident:
            # Trip circuit breaker on budget exhaustion
            self.circuit_breaker_tripped = True
            self.circuit_breaker_reason = f"Execution budget exhausted ({executed_count}/{policy.max_actions_per_incident} actions run for incident {action.incident_id})."
            policy.circuit_breaker_tripped = True
            policy.circuit_breaker_reason = self.circuit_breaker_reason
            await session.flush()
            raise RemediationSecurityException(
                f"Execution budget exceeded: Maximum {policy.max_actions_per_incident} remediation attempts reached for this incident."
            )

        # 5. Concurrency Enforcement
        svc = action.target_service_name
        if svc in self._active_executions and self._active_executions[svc] != action.id:
            raise RemediationSecurityException(
                f"Concurrency conflict: Service '{svc}' is currently undergoing action '{self._active_executions[svc]}'."
            )

    def mark_execution_start(self, service_name: str, action_id: str):
        self._active_executions[service_name] = action_id

    def mark_execution_end(self, service_name: str):
        if service_name in self._active_executions:
            del self._active_executions[service_name]

    def trip_circuit_breaker(self, reason: str):
        self.circuit_breaker_tripped = True
        self.circuit_breaker_reason = reason
        logger.error(f"[SafetyEngine] Circuit breaker TRIPPED: {reason}")


# Singleton instance
safety_engine = SafetyEngine()
