"""
INCIDENTX AI - Safe Autonomous Incident Resolution Service (Phase 12 Module 12.10)
Coordinates the complete end-to-end incident resolution lifecycle:
Root Cause Findings (Phase 11) -> Planning (12.1) -> Risk Assessment (12.3) ->
Approval Gating (12.4) -> Pre-Execution Safety (12.6) -> Controlled Execution (12.5) ->
Recovery Verification (12.8) -> Automated Rollback if Failed (12.7) ->
Lifecycle Update to RESOLVED (Phase 9 Module 9.1).
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.remediation import RemediationAction
from backend.app.services.incident.lifecycle_engine import incident_lifecycle_engine
from backend.app.services.incident.timeline_engine import incident_timeline_engine
from backend.app.services.resolution.action_library import action_library
from backend.app.services.resolution.approval_engine import approval_engine
from backend.app.services.resolution.execution_engine import execution_engine
from backend.app.services.resolution.kill_switch import kill_switch
from backend.app.services.resolution.planning_engine import planning_engine
from backend.app.services.resolution.recovery_verifier import recovery_verifier
from backend.app.services.resolution.risk_engine import risk_engine
from backend.app.services.resolution.rollback_engine import rollback_engine
from backend.app.services.resolution.safety_validator import safety_validator
from backend.app.services.resolution.schemas import (
    ApprovalRecord,
    ApprovalStatus,
    ExecutionStatus,
    KillSwitchState,
    RecoveryStatus,
    ResolutionActionItem,
    ResolutionPlan,
)
from backend.app.services.root_cause.root_cause_service import root_cause_service
from backend.app.services.root_cause.schemas import RootCauseReport


class AutonomousResolutionService:
    """
    Master Coordinator for Safe Autonomous Incident Resolution.
    Enforces strict gating: no state transition to RESOLVED without verified empirical recovery.
    """

    def __init__(self):
        # In-memory plan store (plan_id -> ResolutionPlan) and index (incident_id -> plan_id)
        self._plans: Dict[str, ResolutionPlan] = {}
        self._incident_to_plan: Dict[str, str] = {}

    def get_plan(self, plan_id: str) -> Optional[ResolutionPlan]:
        return self._plans.get(plan_id)

    def get_plan_for_incident(self, incident_id: str) -> Optional[ResolutionPlan]:
        plan_id = self._incident_to_plan.get(incident_id)
        if plan_id:
            return self._plans.get(plan_id)
        return None

    async def generate_plan_for_incident(
        self,
        incident_id: str,
        session: AsyncSession,
        environment: Optional[str] = None,
        target_service: Optional[str] = None,
    ) -> ResolutionPlan:
        """
        Synthesizes a resolution plan from Phase 11 Root Cause Intelligence findings.
        """
        # 1. Fetch incident record
        stmt = select(Incident).where(Incident.id == incident_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found.")

        target_env = environment or incident.environment or "DEMOMESH"
        target_svc = target_service or incident.impact_scope or "payment-service"

        # 2. Fetch or evaluate Phase 11 Root Cause Intelligence
        rc_report = await root_cause_service.evaluate_incident_root_cause(
            incident_id=incident_id,
            session=session,
            affected_service=target_svc,
        )

        # 3. Formulate structured plan (Module 12.1)
        plan = planning_engine.generate_remediation_plan(
            incident_id=incident_id,
            root_cause_report=rc_report,
            environment=target_env,
            target_service_override=target_svc,
            incident_severity=incident.severity or "P2",
        )

        # 4. Cache plan
        self._plans[plan.plan_id] = plan
        self._incident_to_plan[incident_id] = plan.plan_id

        # 5. Persist RemediationAction record for Phase 4-10 database compatibility
        action_item = plan.proposed_actions[0]
        db_action = RemediationAction(
            id=plan.plan_id,
            incident_id=incident_id,
            action_id=action_item.action_id,
            name=action_item.name,
            description=action_item.expected_outcome,
            action_type=action_item.action_type,
            target_service_name=action_item.target_service_name,
            parameters=json.dumps(action_item.parameters),
            preconditions=json.dumps(action_item.preconditions),
            expected_outcome=action_item.expected_outcome,
            risk_level=action_item.risk_level.value,
            idempotency_key=f"{plan.plan_id}:{action_item.action_id}",
            approval_status=plan.approval_record.approval_status.value,
            status=plan.status,
            execution_mode="CONTROLLED_AUTONOMOUS" if plan.approval_record.approval_status == ApprovalStatus.AUTO_APPROVED else "HUMAN_APPROVAL",
        )
        session.add(db_action)
        await session.flush()

        # 6. Update Phase 9 Incident Lifecycle to REMEDIATION_PENDING
        try:
            await incident_lifecycle_engine.transition(
                incident_id=incident_id,
                target_state="REMEDIATION_PENDING",
                actor="AutonomousResolutionService",
                actor_type="AI_AGENT",
                reason=f"Remediation plan '{plan.plan_id}' formulated for '{action_item.name}'.",
                session=session,
            )
        except Exception as ex:
            logger.debug(f"[ResolutionService] Lifecycle transition note: {ex}")

        # 7. Record Phase 9 Timeline event
        await incident_timeline_engine.record_event(
            incident_id=incident_id,
            event_type="REMEDIATION_PROPOSED",
            service_name=target_svc,
            title=f"Remediation Plan Formulated: {action_item.name}",
            description=f"Action: {action_item.action_id} | Risk: {plan.overall_risk_level.value} | Approval: {plan.approval_record.approval_status.value}",
            session=session,
        )

        logger.info(f"[ResolutionService] Plan '{plan.plan_id}' generated for incident '{incident_id}'.")
        return plan

    async def approve_plan(
        self,
        incident_id: str,
        approving_user: str,
        user_role: str,
        decision: ApprovalStatus,
        reason: str,
        session: AsyncSession,
        emergency_override: bool = False,
    ) -> ResolutionPlan:
        """
        Records human operator approval or rejection for the incident's active remediation plan.
        """
        plan = self.get_plan_for_incident(incident_id)
        if not plan:
            raise ValueError(f"No active resolution plan found for incident '{incident_id}'.")

        action = plan.proposed_actions[0]
        approval = approval_engine.record_decision(
            approval=plan.approval_record,
            approving_user=approving_user,
            user_role=user_role,
            decision=decision,
            reason=reason,
            current_parameters=action.parameters,
            emergency_override=emergency_override,
        )
        plan.approval_record = approval
        plan.status = approval.approval_status.value
        plan.updated_at = datetime.now(timezone.utc)

        # Record timeline event
        await incident_timeline_engine.record_event(
            incident_id=incident_id,
            event_type="APPROVAL_DECISION",
            service_name=action.target_service_name,
            title=f"Remediation Approval: {decision.value}",
            description=f"Decided by {approving_user} ({user_role}): {reason}",
            session=session,
        )

        logger.info(f"[ResolutionService] Plan '{plan.plan_id}' approval status updated to '{decision.value}'.")
        return plan

    async def execute_resolution(
        self,
        incident_id: str,
        session: AsyncSession,
        auto_rollback_on_failure: bool = True,
    ) -> ResolutionPlan:
        """
        Executes approved resolution plan, runs recovery verification, and updates lifecycle.
        """
        plan = self.get_plan_for_incident(incident_id)
        if not plan:
            raise ValueError(f"No active resolution plan found for incident '{incident_id}'.")

        action = plan.proposed_actions[0]

        # 1. Update Phase 9 Lifecycle to REMEDIATING
        try:
            await incident_lifecycle_engine.transition(
                incident_id=incident_id,
                target_state="REMEDIATING",
                actor="AutonomousResolutionService",
                actor_type="AUTOMATION",
                reason=f"Commencing execution of '{action.name}'.",
                session=session,
            )
        except Exception as ex:
            logger.debug(f"[ResolutionService] Lifecycle transition note: {ex}")

        # 2. Dispatch Controlled Execution (Module 12.5)
        updated_plan = await execution_engine.execute_plan(
            plan=plan,
            cluster_id="k8s-default",
            namespace="default",
            auto_rollback_on_failure=auto_rollback_on_failure,
        )
        self._plans[updated_plan.plan_id] = updated_plan

        # 3. Post-execution Lifecycle Gating
        rec_report = updated_plan.recovery_report
        exec_res = updated_plan.execution_result

        if exec_res and exec_res.status == ExecutionStatus.EXECUTED:
            # Transition to VERIFYING
            try:
                await incident_lifecycle_engine.transition(
                    incident_id=incident_id,
                    target_state="VERIFYING",
                    actor="AutonomousResolutionService",
                    actor_type="AUTOMATION",
                    reason="Execution finished; empirical recovery verification underway.",
                    session=session,
                )
            except Exception as ex:
                logger.debug(f"[ResolutionService] Lifecycle transition note: {ex}")

            # If Recovery is strictly verified, transition to RESOLVED!
            if rec_report and rec_report.status == RecoveryStatus.RECOVERY_SUCCESSFUL:
                try:
                    await incident_lifecycle_engine.transition(
                        incident_id=incident_id,
                        target_state="RESOLVED",
                        actor="AutonomousResolutionService",
                        actor_type="AUTOMATION",
                        reason=f"Incident RESOLVED: {rec_report.summary}",
                        session=session,
                    )
                except Exception as ex:
                    logger.debug(f"[ResolutionService] Lifecycle transition note: {ex}")

                await incident_timeline_engine.record_event(
                    incident_id=incident_id,
                    event_type="RECOVERY_VERIFIED",
                    service_name=action.target_service_name,
                    title="Empirical Recovery Verified: Incident RESOLVED",
                    description=rec_report.summary,
                    session=session,
                )

        elif updated_plan.status in ("ROLLED_BACK", "ROLLBACK_FAILED", "FAILED", "PRE_CHECK_FAILED"):
            await incident_timeline_engine.record_event(
                incident_id=incident_id,
                event_type="REMEDIATION_FAILED",
                service_name=action.target_service_name,
                title=f"Remediation Failed ({updated_plan.status})",
                description=exec_res.error_message if exec_res else "Safety check or execution failure",
                session=session,
            )

        return updated_plan


resolution_service = AutonomousResolutionService()
