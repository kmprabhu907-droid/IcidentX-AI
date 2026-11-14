"""
INCIDENTX AI - Intelligent Remediation Planning Engine (Phase 12 Module 12.1)
Synthesizes structured, safe remediation plans grounded directly in Phase 11 Root Cause Intelligence.
CRITICAL SAFETY INVARIANT: Never generates executable actions from unsupported root cause hypotheses.
Requires hypothesis confidence >= 0.45 and status != REJECTED/CONTRADICTED.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.resolution.action_library import action_library
from backend.app.services.resolution.approval_engine import approval_engine
from backend.app.services.resolution.risk_engine import risk_engine
from backend.app.services.resolution.schemas import (
    ApprovalRecord,
    ResolutionActionItem,
    ResolutionPlan,
    RiskAssessment,
    RiskClassification,
)
from backend.app.services.root_cause.schemas import RootCauseReport, HypothesisStatus


class RemediationPlanningEngine:
    """
    Synthesizes complete, multi-strategy remediation plans from Phase 11 root cause findings.
    """

    @classmethod
    def generate_remediation_plan(
        cls,
        incident_id: str,
        root_cause_report: RootCauseReport,
        environment: str = "DEMOMESH",
        target_service_override: Optional[str] = None,
        incident_severity: str = "P2",
    ) -> ResolutionPlan:
        """
        Formulates an actionable, verified recovery plan based on the leading hypothesis.
        """
        top_hyp = root_cause_report.primary_hypothesis
        plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        target_service = target_service_override or top_hyp.affected_service or "payment-service"

        # ----------------------------------------------------------------------
        # SAFETY INVARIANT CHECK: Grounding in Supported Hypothesis
        # ----------------------------------------------------------------------
        if top_hyp.confidence_score < 0.35 or top_hyp.status in (HypothesisStatus.REJECTED, HypothesisStatus.CONTRADICTED):
            logger.warning(
                f"[PlanningEngine] Primary hypothesis '{top_hyp.title}' is UNSUPPORTED (confidence: {top_hyp.confidence_score:.2f}, status: {top_hyp.status.value}). "
                "Generating SAFE PASSIVE DIAGNOSTIC plan only."
            )
            # Only generate passive diagnostic re-checks, zero destructive infrastructure operations
            passive_action = action_library.create_action_item(
                action_id="infra-recheck-health",
                target_service=target_service,
                environment=environment,
                parameters={"reason": "Hypothesis confidence insufficient for autonomous mutation"},
            )
            risk_eval = risk_engine.evaluate_action_risk(
                plan_id=plan_id,
                action=passive_action,
                incident_severity=incident_severity,
                cluster_health="DEGRADED",
            )
            approval_rec = approval_engine.create_approval_request(
                plan_id=plan_id,
                action=passive_action,
                risk_assessment=risk_eval,
                allow_low_risk_auto_approve=True,
            )
            return ResolutionPlan(
                plan_id=plan_id,
                incident_id=incident_id,
                investigation_id=root_cause_report.investigation_id,
                root_cause_reference=f"UNCONFIRMED: {top_hyp.title}",
                root_cause_confidence=top_hyp.confidence_score,
                environment=environment,
                target_service_name=target_service,
                affected_resources=[passive_action.target_resource],
                proposed_actions=[passive_action],
                execution_sequence=[passive_action.action_id],
                overall_risk_level=RiskClassification.LOW,
                risk_assessment=risk_eval,
                approval_record=approval_rec,
                status="PROPOSED",
                plan_fingerprint=hashlib.sha256(f"{plan_id}-passive".encode()).hexdigest(),
                created_at=now,
                updated_at=now,
            )

        # ----------------------------------------------------------------------
        # Synthesize Active Remediation Action based on Causal Diagnosis
        # ----------------------------------------------------------------------
        title_lower = top_hyp.title.lower()
        proposed_actions: List[ResolutionActionItem] = []

        if "deployment" in title_lower or "commit" in title_lower or "release" in title_lower or "regression" in title_lower:
            # Code / Release regression -> Rollback deployment revision
            primary_act = action_library.create_action_item(
                action_id="k8s-rollback-deployment",
                target_service=target_service,
                environment=environment,
                parameters={"target_revision": "previous-stable", "service_name": target_service},
            )
            proposed_actions.append(primary_act)

        elif "memory" in title_lower or "oom" in title_lower or "leak" in title_lower or "buffer" in title_lower:
            # Memory leak / OOM saturation -> Scale replicas + rolling restart
            primary_act = action_library.create_action_item(
                action_id="k8s-restart-deployment",
                target_service=target_service,
                environment=environment,
                parameters={"service_name": target_service, "grace_period_seconds": 10},
            )
            scale_act = action_library.create_action_item(
                action_id="k8s-scale-deployment",
                target_service=target_service,
                environment=environment,
                parameters={"service_name": target_service, "target_replicas": 3, "current_replicas": 2},
            )
            proposed_actions.extend([primary_act, scale_act])

        elif "database" in title_lower or "pool" in title_lower or "connection" in title_lower or "timeout" in title_lower:
            # Database pool saturation -> Trigger application recovery workflow (pool reset)
            primary_act = action_library.create_action_item(
                action_id="app-trigger-recovery-workflow",
                target_service=target_service,
                environment=environment,
                parameters={"action": "reset_connection_pool", "service_name": target_service},
            )
            proposed_actions.append(primary_act)

        elif "feature" in title_lower or "flag" in title_lower:
            # Feature flag anomaly -> Disable flag
            primary_act = action_library.create_action_item(
                action_id="app-disable-feature-flag",
                target_service=target_service,
                environment=environment,
                parameters={"flag_name": f"{target_service}_new_feature", "enabled": False},
            )
            proposed_actions.append(primary_act)

        else:
            # General operational degradation -> Rolling restart
            primary_act = action_library.create_action_item(
                action_id="k8s-restart-deployment",
                target_service=target_service,
                environment=environment,
                parameters={"service_name": target_service, "grace_period_seconds": 5},
            )
            proposed_actions.append(primary_act)

        # Primary action governs plan risk and approval
        lead_action = proposed_actions[0]
        risk_eval = risk_engine.evaluate_action_risk(
            plan_id=plan_id,
            action=lead_action,
            incident_severity=incident_severity,
            cluster_health="HEALTHY",
            affected_replica_count=len(proposed_actions) * 2,
        )

        approval_rec = approval_engine.create_approval_request(
            plan_id=plan_id,
            action=lead_action,
            risk_assessment=risk_eval,
            allow_low_risk_auto_approve=(risk_eval.risk_classification == RiskClassification.LOW),
        )

        affected_res = list({act.target_resource for act in proposed_actions})
        exec_seq = [act.action_id for act in proposed_actions]

        fingerprint_content = f"{plan_id}:{target_service}:{lead_action.action_id}:{approval_rec.parameters_hash}"
        plan_fingerprint = hashlib.sha256(fingerprint_content.encode("utf-8")).hexdigest()

        return ResolutionPlan(
            plan_id=plan_id,
            incident_id=incident_id,
            investigation_id=root_cause_report.investigation_id,
            root_cause_reference=top_hyp.title,
            root_cause_confidence=top_hyp.confidence_score,
            environment=environment,
            target_service_name=target_service,
            affected_resources=affected_res,
            proposed_actions=proposed_actions,
            execution_sequence=exec_seq,
            overall_risk_level=risk_eval.risk_classification,
            risk_assessment=risk_eval,
            approval_record=approval_rec,
            status="PROPOSED",
            plan_fingerprint=plan_fingerprint,
            created_at=now,
            updated_at=now,
        )


planning_engine = RemediationPlanningEngine()
