"""
INCIDENTX AI - Phase 12 Safe Autonomous Incident Resolution Engine
Package initialization and clean module exports.
"""

from backend.app.services.resolution.action_library import action_library, RemediationActionLibrary
from backend.app.services.resolution.approval_engine import approval_engine, ApprovalWorkflowEngine
from backend.app.services.resolution.execution_engine import execution_engine, ControlledExecutionEngine
from backend.app.services.resolution.kill_switch import kill_switch, RemediationKillSwitch
from backend.app.services.resolution.planning_engine import planning_engine, RemediationPlanningEngine
from backend.app.services.resolution.recovery_verifier import recovery_verifier, EmpiricalRecoveryVerifier
from backend.app.services.resolution.risk_engine import risk_engine, IntelligentRiskEngine
from backend.app.services.resolution.rollback_engine import rollback_engine, AutomatedRollbackEngine
from backend.app.services.resolution.safety_validator import safety_validator, PreExecutionSafetyEngine
from backend.app.services.resolution.resolution_service import resolution_service, AutonomousResolutionService
from backend.app.services.resolution.schemas import (
    ActionCategory,
    ActionExecutionResult,
    ApprovalRecord,
    ApprovalStatus,
    ExecutionStatus,
    KillSwitchState,
    PreExecutionCheckResult,
    RecoveryMetricComparison,
    RecoveryStatus,
    RecoveryVerificationReport,
    ResolutionActionItem,
    ResolutionPlan,
    ResourceStateSnapshot,
    RiskAssessment,
    RiskClassification,
    RollbackExecutionResult,
)

__all__ = [
    "action_library",
    "approval_engine",
    "execution_engine",
    "kill_switch",
    "planning_engine",
    "recovery_verifier",
    "risk_engine",
    "rollback_engine",
    "safety_validator",
    "resolution_service",
    "RemediationActionLibrary",
    "ApprovalWorkflowEngine",
    "ControlledExecutionEngine",
    "RemediationKillSwitch",
    "RemediationPlanningEngine",
    "EmpiricalRecoveryVerifier",
    "IntelligentRiskEngine",
    "AutomatedRollbackEngine",
    "PreExecutionSafetyEngine",
    "AutonomousResolutionService",
    "ActionCategory",
    "ActionExecutionResult",
    "ApprovalRecord",
    "ApprovalStatus",
    "ExecutionStatus",
    "KillSwitchState",
    "PreExecutionCheckResult",
    "RecoveryMetricComparison",
    "RecoveryStatus",
    "RecoveryVerificationReport",
    "ResolutionActionItem",
    "ResolutionPlan",
    "ResourceStateSnapshot",
    "RiskAssessment",
    "RiskClassification",
    "RollbackExecutionResult",
]
