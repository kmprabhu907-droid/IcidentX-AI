"""
INCIDENTX AI - Remediation Execution Engine
Orchestrates safe, validated action execution exclusively within the isolated local simulation environment.
Enforces precondition validation, idempotency, timeouts, snapshot capture, and automatic rollback on failure.
"""

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import IncidentXException
from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.remediation import RemediationAction
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.remediation.registry import remediation_registry
from backend.app.services.remediation.safety import safety_engine


class RemediationExecutionException(IncidentXException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class RemediationExecutor:
    """
    Executes recovery actions with safety validation, before/after snapshots,
    empirical verification, and rollback lifecycle.
    """

    async def execute_action(
        self,
        action_db_id: str,
        session: AsyncSession,
        is_autonomous_trigger: bool = False,
    ) -> RemediationAction:
        """Execute a proposed remediation action."""
        # 1. Fetch action record
        stmt = select(RemediationAction).where(RemediationAction.id == action_db_id)
        res = await session.execute(stmt)
        action = res.scalar_one_or_none()
        if not action:
            raise RemediationExecutionException(f"Remediation action '{action_db_id}' not found.")

        # Check if already executed (Idempotency enforcement)
        if action.status in ["EXECUTING", "EXECUTED", "VERIFIED"]:
            raise RemediationExecutionException(
                f"Action '{action.id}' has already been processed (status={action.status}). Idempotency key: {action.idempotency_key}"
            )

        # 2. Look up registry implementation
        act_impl = remediation_registry.get_action(action.action_id)
        if not act_impl:
            raise RemediationExecutionException(f"Action ID '{action.action_id}' is not in the controlled action registry.")

        # 3. Parse and validate parameters against Pydantic schema
        try:
            params = json.loads(action.parameters) if action.parameters else {}
        except Exception as e:
            raise RemediationExecutionException(f"Failed to parse parameters JSON: {e}")

        try:
            act_impl.validate_parameters(params)
        except Exception as e:
            action.status = "FAILED"
            action.error_message = f"Parameter validation failed: {e}"
            await session.flush()
            raise RemediationExecutionException(f"Parameter validation failed for '{action.action_id}': {e}")

        # 4. Enforce Safety Policy & Approval Invariants
        await safety_engine.validate_execution_safety(
            action=action,
            session=session,
            is_autonomous_trigger=is_autonomous_trigger,
        )

        # 5. Check Preconditions
        pre_ok, pre_reason = await act_impl.check_preconditions(params, {"incident_id": action.incident_id})
        if not pre_ok:
            action.status = "FAILED"
            action.error_message = f"Precondition failed: {pre_reason}"
            await session.flush()
            raise RemediationExecutionException(f"Precondition failed for '{action.action_id}': {pre_reason}")

        # 6. Mark execution start & acquire concurrency lock
        safety_engine.mark_execution_start(action.target_service_name, action.id)
        action.status = "EXECUTING"
        action.executed_at = datetime.now(timezone.utc)

        # Capture Before Telemetry Snapshot
        before_metrics = demo_mesh.get_latest_metrics()
        action.snapshot_before = json.dumps(before_metrics)
        await session.flush()

        start_time = time.perf_counter()
        exec_log = []
        exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] Preconditions satisfied: {pre_reason}")
        exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] Beginning simulated execution for '{action.action_id}'")

        try:
            # 7. Execute within simulated environment with timeout
            exec_res = await asyncio.wait_for(
                act_impl.execute_simulated(params, {"incident_id": action.incident_id}),
                timeout=action.timeout_seconds,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            action.execution_duration_ms = elapsed_ms
            exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] Simulation execution completed in {elapsed_ms}ms: {exec_res.get('message')}")

            # Advance mesh clock so fresh metrics settle
            await asyncio.sleep(0.05)

            # 8. Capture After Telemetry Snapshot
            after_metrics = demo_mesh.get_latest_metrics()
            action.snapshot_after = json.dumps(after_metrics)

            # 9. Independent Recovery Verification
            verif_status, verif_details = await act_impl.verify_recovery(params, before_metrics, after_metrics)
            action.verification_status = verif_status
            action.verification_details = json.dumps(verif_details)
            exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] Verification completed: Status={verif_status}, Details={verif_details}")

            if verif_status in ["VERIFIED", "PARTIALLY_VERIFIED"]:
                action.status = "EXECUTED"
                action.error_message = None
                action.rollback_status = "AVAILABLE"
                logger.info(f"[RemediationExecutor] Action '{action.id}' VERIFIED successfully.")
            else:
                # Verification Failed or Inconclusive: Trigger automatic rollback
                action.status = "FAILED"
                action.error_message = f"Recovery verification {verif_status}. Metrics did not normalize to healthy baseline."
                logger.warning(f"[RemediationExecutor] Verification {verif_status}. Initiating automatic rollback for '{action.id}'.")

                # Automatic Rollback
                action.rollback_status = "EXECUTING"
                rollback_res = await act_impl.rollback_simulated(params, {"incident_id": action.incident_id})
                action.rollback_status = "ROLLED_BACK"
                action.rollback_log = json.dumps(rollback_res)
                exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] Automatic rollback applied: {rollback_res}")

                # Trip circuit breaker to prevent cascading autonomous actions
                safety_engine.trip_circuit_breaker(
                    f"Action '{action.action_id}' failed recovery verification on {action.target_service_name}."
                )

        except asyncio.TimeoutError:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            action.status = "FAILED"
            action.execution_duration_ms = elapsed_ms
            action.error_message = f"Execution timed out after {action.timeout_seconds}s."
            exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] TIMEOUT: Execution exceeded {action.timeout_seconds}s.")
            safety_engine.trip_circuit_breaker(f"Action '{action.action_id}' timed out on {action.target_service_name}.")

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            action.status = "FAILED"
            action.execution_duration_ms = elapsed_ms
            action.error_message = f"Execution exception: {str(e)}"
            exec_log.append(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {str(e)}")
            safety_engine.trip_circuit_breaker(f"Action '{action.action_id}' failed with exception: {e}")

        finally:
            safety_engine.mark_execution_end(action.target_service_name)
            action.execution_log = "\n".join(exec_log)

            # Record Audit Log
            audit = AuditLog(
                incident_id=action.incident_id,
                actor_type="AUTONOMOUS_ENGINE" if is_autonomous_trigger else "OPERATOR",
                actor_id=action.approved_by or "system",
                action=f"REMEDIATION_{action.status}",
                resource_type="REMEDIATION_ACTION",
                resource_id=action.id,
                details=f"Action '{action.name}' on '{action.target_service_name}' status: {action.status}, verification: {action.verification_status}",
            )
            session.add(audit)
            await session.flush()

        return action

    async def rollback_action(
        self,
        action_db_id: str,
        session: AsyncSession,
        requested_by: str = "operator",
    ) -> RemediationAction:
        """Manually trigger rollback for an executed remediation action."""
        stmt = select(RemediationAction).where(RemediationAction.id == action_db_id)
        res = await session.execute(stmt)
        action = res.scalar_one_or_none()
        if not action:
            raise RemediationExecutionException(f"Remediation action '{action_db_id}' not found.")

        if action.rollback_status == "ROLLED_BACK":
            raise RemediationExecutionException(f"Action '{action_db_id}' has already been rolled back.")

        act_impl = remediation_registry.get_action(action.action_id)
        if not act_impl:
            raise RemediationExecutionException(f"Registry implementation for '{action.action_id}' not found.")

        params = json.loads(action.parameters) if action.parameters else {}
        action.rollback_status = "EXECUTING"
        await session.flush()

        try:
            rollback_res = await act_impl.rollback_simulated(params, {"incident_id": action.incident_id})
            action.rollback_status = "ROLLED_BACK"
            action.rollback_log = json.dumps(rollback_res)
            logger.info(f"[RemediationExecutor] Action '{action.id}' rolled back successfully.")

            audit = AuditLog(
                incident_id=action.incident_id,
                actor_type="OPERATOR",
                actor_id=requested_by,
                action="REMEDIATION_ROLLED_BACK",
                resource_type="REMEDIATION_ACTION",
                resource_id=action.id,
                details=f"Manual rollback executed by {requested_by} for {action.name}.",
            )
            session.add(audit)
            await session.flush()

        except Exception as e:
            action.rollback_status = "ROLLBACK_FAILED"
            action.error_message = f"Rollback failed: {e}"
            await session.flush()
            raise RemediationExecutionException(f"Rollback failed: {e}")

        return action


# Singleton instance
remediation_executor = RemediationExecutor()
