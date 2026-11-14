"""
INCIDENTX AI - Hackathon Demonstration & End-to-End Orchestration Schemas (Phase 16)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DemonstrationScenarioID(str, Enum):
    SCENARIO_A = "SCENARIO_A"  # Deployment-Induced API Latency
    SCENARIO_B = "SCENARIO_B"  # Kubernetes Resource Exhaustion (OOMKilled)
    SCENARIO_C = "SCENARIO_C"  # Cascading Service Failure & Circuit Breaking


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OrchestrationStep(BaseModel):
    """Single stage in the 16-step autonomous SRE orchestration loop."""
    step_number: int
    name: str
    phase_ref: str
    status: StepStatus = StepStatus.PENDING
    details: str = ""
    evidence: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DemonstrationScenario(BaseModel):
    """Metadata for a repeatable hackathon scenario."""
    scenario_id: DemonstrationScenarioID
    title: str
    target_service: str
    severity: str = "SEV-1"
    environment: str = "DEMOMESH"
    fault_type: str
    description: str
    expected_root_cause: str
    proposed_remediation: str
    is_active: bool = False


class OrchestrationExecutionResult(BaseModel):
    """Full execution trace of an autonomous incident lifecycle."""
    execution_id: str
    scenario_id: DemonstrationScenarioID
    incident_id: str
    title: str
    severity: str
    target_service: str
    environment: str
    total_duration_seconds: float = 0.0
    steps: List[OrchestrationStep] = Field(default_factory=list)
    
    # Culmination Outputs
    root_cause_ruling: str = ""
    confidence_score: float = 0.0
    remediation_executed: str = ""
    human_approved: bool = True
    approver_role: str = "INCIDENT_COMMANDER"
    recovery_status: str = "RECOVERY_SUCCESSFUL"
    postmortem_id: Optional[str] = None
    policy_version: str = "pol-v1-base"
    is_completed: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
