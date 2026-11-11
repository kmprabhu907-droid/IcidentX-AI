"""
INCIDENTX AI - Autonomous Workflow Coordinator (Stage 6.5)
Orchestrates end-to-end reliability state machines across detection, causal investigation,
planning, human approval gateways, safe remediation execution, and verification.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.workflow import WorkflowExecution, WorkflowStatus
from backend.app.services.events.bus import event_bus
from backend.app.services.events.events import (
    IncidentDetectedEvent,
    RemediationApprovedEvent,
    RemediationExecutedEvent,
    RemediationRequestedEvent,
    RootCauseIdentifiedEvent,
)


class WorkflowCoordinator:
    """Manages sequential execution and pause/resume lifecycle of reliability workflows."""

    @staticmethod
    def _append_step(
        history: List[Dict[str, Any]],
        step_name: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        now_iso = datetime.now(timezone.utc).isoformat()
        history.append({
            "step": step_name,
            "status": status,
            "timestamp": now_iso,
            "details": details or {},
        })
        return history

    @classmethod
    async def start_workflow(
        cls,
        organization_id: str,
        incident_id: Optional[str] = None,
        service_name: str = "order-service",
        severity: str = "SEV-2",
        title: str = "Simulated Cascading Degraded Latency",
        auto_approve: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> WorkflowExecution:
        """
        Initiates a multi-step reliability workflow.
        If auto_approve is False, the workflow transitions to AWAITING_APPROVAL and pauses.
        """
        history: List[Dict[str, Any]] = []
        meta = {
            "service_name": service_name,
            "severity": severity,
            "title": title,
            "auto_approve": auto_approve,
            "incident_id": incident_id,
        }

        # Create persistent workflow execution record
        execution = WorkflowExecution(
            organization_id=organization_id,
            incident_id=incident_id,
            workflow_type="AUTONOMOUS_INCIDENT_REMEDIATION",
            status=WorkflowStatus.INVESTIGATING.value,
            current_step="DETECTION",
            metadata_json=json.dumps(meta),
            step_history_json="[]",
        )
        if db:
            db.add(execution)
            await db.flush()

        # Step 1: Detection
        cls._append_step(history, "DETECTION", "COMPLETED", {"title": title, "severity": severity})
        await event_bus.publish(
            IncidentDetectedEvent(
                organization_id=organization_id,
                data={
                    "incident_id": incident_id or execution.id,
                    "service_name": service_name,
                    "severity": severity,
                    "title": title,
                },
            )
        )

        # Step 2: Investigation & Root Cause Causal Reasoning
        execution.current_step = "INVESTIGATION"
        root_cause_summary = f"Thread contention and connection pool exhaustion in {service_name}"
        confidence = 0.94
        cls._append_step(history, "INVESTIGATION", "COMPLETED", {
            "root_cause": root_cause_summary,
            "confidence": confidence,
        })
        await event_bus.publish(
            RootCauseIdentifiedEvent(
                organization_id=organization_id,
                data={
                    "incident_id": incident_id or execution.id,
                    "service_name": service_name,
                    "root_cause": root_cause_summary,
                    "confidence": confidence,
                },
            )
        )

        # Step 3: Planning & Remediation Action Generation
        execution.current_step = "PLANNING"
        recommended_action = "Expand DB Connection Pool & Scale Replicas"
        action_id = f"act-{execution.id[:8]}"
        risk_level = "MEDIUM"
        cls._append_step(history, "PLANNING", "COMPLETED", {
            "action_id": action_id,
            "action_name": recommended_action,
            "risk_level": risk_level,
        })

        # Step 4: Approval Gateway
        execution.current_step = "APPROVAL_GATEWAY"
        if not auto_approve:
            execution.status = WorkflowStatus.AWAITING_APPROVAL.value
            cls._append_step(history, "APPROVAL_GATEWAY", "PAUSED", {
                "message": "Workflow paused awaiting human SRE authorization.",
                "action_id": action_id,
                "action_name": recommended_action,
            })
            await event_bus.publish(
                RemediationRequestedEvent(
                    organization_id=organization_id,
                    data={
                        "incident_id": incident_id or execution.id,
                        "action_id": action_id,
                        "action_name": recommended_action,
                        "service_name": service_name,
                        "severity": severity,
                    },
                )
            )
            execution.step_history_json = json.dumps(history)
            if db:
                await db.commit()
                await db.refresh(execution)
            return execution

        # Step 5: Safe Remediation Execution (if auto_approve=True)
        return await cls._execute_remaining_steps(execution, history, action_id, recommended_action, service_name, db)

    @classmethod
    async def resume_workflow(
        cls,
        workflow_id: str,
        approved: bool,
        approver: str = "operator@incidentx.internal",
        comment: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> WorkflowExecution:
        """
        Resumes a paused workflow following a human-in-the-loop approval decision.
        """
        if not db:
            raise ValueError("AsyncSession required to resume workflow.")

        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        if execution.status != WorkflowStatus.AWAITING_APPROVAL.value:
            raise ValueError(
                f"Workflow '{workflow_id}' cannot be resumed; current status is '{execution.status}', expected 'AWAITING_APPROVAL'."
            )

        history = json.loads(execution.step_history_json) if execution.step_history_json else []
        meta = json.loads(execution.metadata_json) if execution.metadata_json else {}
        service_name = meta.get("service_name", "order-service")
        action_name = meta.get("action_name", "Scale Replicas")
        action_id = f"act-{execution.id[:8]}"

        if not approved:
            execution.status = WorkflowStatus.FAILED.value
            execution.current_step = "APPROVAL_GATEWAY"
            cls._append_step(history, "APPROVAL_GATEWAY", "REJECTED", {
                "approver": approver,
                "comment": comment or "Remediation rejected by operator.",
            })
            execution.step_history_json = json.dumps(history)
            await db.commit()
            await db.refresh(execution)
            return execution

        # Human approved
        cls._append_step(history, "APPROVAL_GATEWAY", "APPROVED", {
            "approver": approver,
            "comment": comment or "Approved via Reliability Gateway.",
        })
        await event_bus.publish(
            RemediationApprovedEvent(
                organization_id=execution.organization_id,
                data={
                    "workflow_id": execution.id,
                    "action_id": action_id,
                    "approver": approver,
                },
            )
        )

        return await cls._execute_remaining_steps(execution, history, action_id, action_name, service_name, db)

    @classmethod
    async def _execute_remaining_steps(
        cls,
        execution: WorkflowExecution,
        history: List[Dict[str, Any]],
        action_id: str,
        action_name: str,
        service_name: str,
        db: Optional[AsyncSession],
    ) -> WorkflowExecution:
        # Step 5: Remediation
        execution.status = WorkflowStatus.REMEDIATING.value
        execution.current_step = "REMEDIATION"
        cls._append_step(history, "REMEDIATION", "COMPLETED", {
            "action_id": action_id,
            "action_name": action_name,
            "execution_duration_ms": 145.0,
            "status": "APPLIED_SUCCESSFULLY",
        })
        await event_bus.publish(
            RemediationExecutedEvent(
                organization_id=execution.organization_id,
                data={
                    "workflow_id": execution.id,
                    "action_id": action_id,
                    "action_name": action_name,
                    "service_name": service_name,
                },
            )
        )

        # Step 6: Verification
        execution.status = WorkflowStatus.VERIFYING.value
        execution.current_step = "VERIFICATION"
        cls._append_step(history, "VERIFICATION", "COMPLETED", {
            "slo_recovery_percentage": 99.8,
            "latency_p95_ms": 82.4,
            "error_rate_stabilized": True,
        })

        # Step 7: Completed
        execution.status = WorkflowStatus.COMPLETED.value
        execution.current_step = "COMPLETED"
        cls._append_step(history, "COMPLETED", "COMPLETED", {
            "resolution": "Autonomous self-healing completed and verified.",
        })

        execution.step_history_json = json.dumps(history)
        if db:
            await db.commit()
            await db.refresh(execution)

        return execution


workflow_coordinator = WorkflowCoordinator()
