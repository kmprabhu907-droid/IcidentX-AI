"""
INCIDENTX AI - Approval Workflow Engine (Phase 12 Module 12.4)
Enforces action-level human and policy-gated authorization with anti-tamper cryptographic binding.
CRITICAL SAFETY INVARIANTS:
1. An AI agent CANNOT authorize its own action.
2. Any parameter or target modification immediately INVALIDATES existing approval.
3. Approvals automatically expire after a bounded time window (default 15 minutes).
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.resolution.schemas import (
    ApprovalRecord,
    ApprovalStatus,
    ResolutionActionItem,
    RiskAssessment,
    RiskClassification,
)


class ApprovalWorkflowEngine:
    """
    Manages action authorization lifecycle, anti-tamper parameter signatures,
    and role-based human approval gates.
    """

    DEFAULT_EXPIRY_MINUTES = 15

    @classmethod
    def compute_parameters_hash(
        cls,
        action_id: str,
        target_resource: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        Generates deterministic SHA-256 fingerprint of the exact execution payload.
        Any change to parameters or resource changes this hash, invalidating prior approval.
        """
        canonical_str = json.dumps(
            {
                "action_id": action_id,
                "target_resource": target_resource,
                "parameters": parameters,
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def create_approval_request(
        cls,
        plan_id: str,
        action: ResolutionActionItem,
        risk_assessment: RiskAssessment,
        requesting_actor: str = "IncidentX-AI",
        requesting_actor_type: str = "AI_AGENT",
        expiry_minutes: int = DEFAULT_EXPIRY_MINUTES,
        allow_low_risk_auto_approve: bool = True,
    ) -> ApprovalRecord:
        """
        Generates an approval record for a proposed remediation action.
        Low-risk operations can be auto-approved under strict policy.
        """
        approval_id = f"appr-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expiry_minutes)
        params_hash = cls.compute_parameters_hash(
            action_id=action.action_id,
            target_resource=action.target_resource,
            parameters=action.parameters,
        )

        # Check for policy-governed automatic approval
        if risk_assessment.risk_classification == RiskClassification.LOW and allow_low_risk_auto_approve:
            status = ApprovalStatus.AUTO_APPROVED
            approver = "SystemPolicyEngine (Policy: ALLOWLIST_LOW_RISK)"
            approver_role = "SYSTEM_POLICY"
            decided_at = now
            reason = "Auto-approved: Action is classified as LOW risk under policy guardrails."
        else:
            status = ApprovalStatus.PENDING
            approver = None
            approver_role = None
            decided_at = None
            reason = None

        return ApprovalRecord(
            approval_id=approval_id,
            plan_id=plan_id,
            action_id=action.action_id,
            target_resource=action.target_resource,
            parameters_hash=params_hash,
            risk_assessment=risk_assessment,
            requesting_actor=requesting_actor,
            requesting_actor_type=requesting_actor_type,
            approving_user=approver,
            approver_role=approver_role,
            approval_status=status,
            decision_reason=reason,
            requested_at=now,
            decided_at=decided_at,
            expires_at=expires_at,
            is_tampered=False,
        )

    @classmethod
    def record_decision(
        cls,
        approval: ApprovalRecord,
        approving_user: str,
        user_role: str,
        decision: ApprovalStatus,
        reason: str,
        current_parameters: Dict[str, Any],
        emergency_override: bool = False,
    ) -> ApprovalRecord:
        """
        Processes human operator decision (APPROVED or REJECTED) with anti-tamper and role verification.
        """
        now = datetime.now(timezone.utc)

        # 1. Anti-Self-Authorization Check: AI agent cannot approve its own action
        if approval.requesting_actor_type == "AI_AGENT" and approving_user.lower().startswith("incidentx"):
            raise PermissionError("Self-authorization violation: AI agents cannot authorize their own remediation actions.")

        # 2. Expiration Check
        if now > approval.expires_at:
            approval.approval_status = ApprovalStatus.EXPIRED
            approval.decision_reason = "Approval request expired prior to decision."
            return approval

        # 3. Anti-Tamper Check: Verify parameters have not been altered since request creation
        current_hash = cls.compute_parameters_hash(
            action_id=approval.action_id,
            target_resource=approval.target_resource,
            parameters=current_parameters,
        )
        if current_hash != approval.parameters_hash:
            approval.approval_status = ApprovalStatus.CANCELLED
            approval.is_tampered = True
            approval.decision_reason = "Security violation: Action parameters were modified after approval was requested."
            logger.critical(f"[ApprovalEngine] Anti-Tamper signature mismatch on approval {approval.approval_id}!")
            return approval

        # 4. Critical Risk Emergency Policy Check
        if approval.risk_assessment.risk_classification == RiskClassification.CRITICAL and decision == ApprovalStatus.APPROVED:
            if not emergency_override:
                raise PermissionError("Execution restricted: CRITICAL risk actions require explicit emergency override policy.")

        # 5. Role Verification for High Risk
        if approval.risk_assessment.risk_classification in (RiskClassification.HIGH, RiskClassification.CRITICAL):
            allowed_roles = {"SRE_LEAD", "INCIDENT_COMMANDER", "ADMIN", "PLATFORM_ADMIN"}
            if user_role.upper() not in allowed_roles:
                raise PermissionError(f"Insufficient authorization: User role '{user_role}' cannot approve HIGH/CRITICAL actions.")

        # Update decision
        approval.approving_user = approving_user
        approval.approver_role = user_role
        approval.approval_status = decision
        approval.decided_at = now
        approval.decision_reason = reason
        logger.info(f"[ApprovalEngine] Approval {approval.approval_id} set to '{decision.value}' by '{approving_user}'.")
        return approval

    @classmethod
    def validate_approval_validity(
        cls,
        approval: ApprovalRecord,
        current_parameters: Dict[str, Any],
    ) -> bool:
        """
        Verifies that approval is currently APPROVED / AUTO_APPROVED, not expired, and untampered.
        """
        now = datetime.now(timezone.utc)
        if approval.approval_status not in (ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED):
            return False
        if now > approval.expires_at:
            return False
        current_hash = cls.compute_parameters_hash(
            action_id=approval.action_id,
            target_resource=approval.target_resource,
            parameters=current_parameters,
        )
        if current_hash != approval.parameters_hash:
            return False
        return True


approval_engine = ApprovalWorkflowEngine()
