"""
INCIDENTX AI - Phase 12 Safe Autonomous Incident Resolution Schemas
Defines structured data contracts for:
- Remediation Plans & Action Library
- Intelligent Risk Assessments
- Approval Workflows with Anti-Tamper Signatures
- Pre-Execution Safety Checks
- Controlled Execution & State Snapshots
- Automated Rollbacks
- Empirical Recovery Verification
- Global Kill Switch & Governance
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskClassification(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    AUTO_APPROVED = "AUTO_APPROVED"


class ExecutionStatus(str, Enum):
    PLANNED = "PLANNED"
    PRE_CHECK_FAILED = "PRE_CHECK_FAILED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


class RecoveryStatus(str, Enum):
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RECOVERY_SUCCESSFUL = "RECOVERY_SUCCESSFUL"
    RECOVERY_PARTIAL = "RECOVERY_PARTIAL"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"


class ActionCategory(str, Enum):
    KUBERNETES = "KUBERNETES"
    APPLICATION = "APPLICATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"


# ==============================================================================
# Remediation Action Contract
# ==============================================================================

class ResolutionActionItem(BaseModel):
    action_id: str
    name: str
    category: ActionCategory
    action_type: str  # restart, scale, rollback, recreate_pods, restore_config, toggle_flag, trigger_workflow
    target_resource: str  # e.g., deployment/payment-service, pod/payment-service-7f6b8, flag/checkout_v2
    target_service_name: str
    environment: str = "DEMOMESH"  # DEMOMESH or KUBERNETES_LIVE
    parameters: Dict[str, Any] = Field(default_factory=dict)
    preconditions: List[str] = Field(default_factory=list)
    expected_outcome: str
    potential_side_effects: List[str] = Field(default_factory=list)
    risk_level: RiskClassification = RiskClassification.LOW
    timeout_seconds: int = 30
    is_reversible: bool = True
    rollback_action_id: Optional[str] = None
    verification_strategy: str


# ==============================================================================
# Risk Assessment Contract (Module 12.3)
# ==============================================================================

class RiskAssessment(BaseModel):
    plan_id: str
    action_id: str
    target_resource: str
    risk_score: float  # 0.0 to 1.0
    risk_classification: RiskClassification
    incident_severity: str
    resource_criticality: str  # TIER_1_CORE, TIER_2_INTERNAL, TIER_3_PERIPHERAL
    affected_resource_count: int
    availability_impact: str
    data_integrity_risk: str
    cluster_health_status: str
    is_reversible: bool
    rollback_available: bool
    potential_failure_scenarios: List[str] = Field(default_factory=list)
    required_safeguards: List[str] = Field(default_factory=list)
    impact_explanation: str
    requires_human_approval: bool
    requires_emergency_override: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Approval Record Contract (Module 12.4)
# ==============================================================================

class ApprovalRecord(BaseModel):
    approval_id: str
    plan_id: str
    action_id: str
    target_resource: str
    parameters_hash: str  # SHA-256 tamper prevention fingerprint
    risk_assessment: RiskAssessment
    requesting_actor: str = "IncidentX-AI"
    requesting_actor_type: str = "AI_AGENT"
    approving_user: Optional[str] = None
    approver_role: Optional[str] = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    decision_reason: Optional[str] = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    expires_at: datetime
    is_tampered: bool = False


# ==============================================================================
# Pre-Execution Safety Check (Module 12.6)
# ==============================================================================

class PreExecutionCheckResult(BaseModel):
    passed: bool
    cluster_identity_verified: bool
    namespace_verified: bool
    resource_identity_verified: bool
    resource_state_healthy: bool
    permissions_verified: bool
    approval_valid: bool
    action_allowlisted: bool
    rollback_ready: bool
    disruption_budget_satisfied: bool
    plan_fresh: bool
    kill_switch_inactive: bool
    failure_reasons: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# State Snapshot Contract
# ==============================================================================

class ResourceStateSnapshot(BaseModel):
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resource_name: str
    resource_version: Optional[str] = None
    replicas_ready: Optional[int] = None
    replicas_desired: Optional[int] = None
    pod_statuses: List[Dict[str, Any]] = Field(default_factory=list)
    config_hash: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    error_rate_percent: Optional[float] = None
    p95_latency_ms: Optional[float] = None


# ==============================================================================
# Execution Result Contract (Module 12.5)
# ==============================================================================

class ActionExecutionResult(BaseModel):
    execution_id: str
    plan_id: str
    action_id: str
    target_resource: str
    environment: str
    status: ExecutionStatus
    pre_state_snapshot: Optional[ResourceStateSnapshot] = None
    post_state_snapshot: Optional[ResourceStateSnapshot] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    idempotency_key: str
    execution_logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    was_rolled_back: bool = False
    rollback_result: Optional[Dict[str, Any]] = None


# ==============================================================================
# Rollback Contract (Module 12.7)
# ==============================================================================

class RollbackExecutionResult(BaseModel):
    rollback_id: str
    original_execution_id: str
    action_id: str
    target_resource: str
    environment: str
    success: bool
    pre_rollback_state: Optional[ResourceStateSnapshot] = None
    post_rollback_state: Optional[ResourceStateSnapshot] = None
    duration_ms: int = 0
    rollback_logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Recovery Verification Contract (Module 12.8)
# ==============================================================================

class RecoveryMetricComparison(BaseModel):
    metric_name: str
    before_value: float
    after_value: float
    unit: str
    threshold: float
    is_healthy: bool


class RecoveryVerificationReport(BaseModel):
    verification_id: str
    incident_id: str
    plan_id: str
    status: RecoveryStatus
    service_name: str
    environment: str
    pod_readiness_ratio: float  # e.g., 1.0 (3/3 ready)
    error_rate_recovered: bool
    latency_recovered: bool
    crash_loop_cleared: bool
    metric_comparisons: List[RecoveryMetricComparison] = Field(default_factory=list)
    health_evidence: List[str] = Field(default_factory=list)
    requires_rollback: bool = False
    summary: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Resolution Plan Contract (Module 12.1)
# ==============================================================================

class ResolutionPlan(BaseModel):
    plan_id: str
    incident_id: str
    investigation_id: Optional[str] = None
    root_cause_reference: str  # Phase 11 primary root cause title
    root_cause_confidence: float
    environment: str = "DEMOMESH"  # DEMOMESH or KUBERNETES_LIVE
    target_service_name: str
    affected_resources: List[str]
    proposed_actions: List[ResolutionActionItem]
    execution_sequence: List[str]  # Ordered action_ids
    overall_risk_level: RiskClassification
    risk_assessment: RiskAssessment
    approval_record: ApprovalRecord
    pre_execution_check: Optional[PreExecutionCheckResult] = None
    execution_result: Optional[ActionExecutionResult] = None
    rollback_result: Optional[RollbackExecutionResult] = None
    recovery_report: Optional[RecoveryVerificationReport] = None
    status: str = "PROPOSED"  # PROPOSED, APPROVED, EXECUTING, EXECUTED, VERIFIED, ROLLED_BACK, FAILED
    plan_fingerprint: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Kill Switch & Governance (Module 12.12)
# ==============================================================================

class KillSwitchState(BaseModel):
    is_active: bool = False
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None
    reason: Optional[str] = None
    in_flight_actions_aborted: int = 0
