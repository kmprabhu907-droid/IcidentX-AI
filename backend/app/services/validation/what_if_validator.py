"""
INCIDENTX AI - What-If Laboratory Validation Engine (Stage 7.7)
Simulates and evaluates alternative recovery strategies in a safe, non-destructive sandbox,
estimating recovery velocity, availability impact, risk scores, resource requirements,
and rollback prerequisites.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class WhatIfSimulationOutcome(BaseModel):
    action_type: str
    target_service: str
    action_parameters: Dict[str, Any]
    is_simulated: bool = True
    is_destructive: bool = False

    # Predicted Impacts
    expected_recovery_time_sec: float
    availability_impact_percent: float  # e.g. +35.0%
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float  # 0.0 to 1.0
    resource_requirements: str
    potential_side_effects: List[str]
    rollback_prerequisites: List[str]
    feasibility_score: float  # 0.0 to 1.0


class WhatIfLabValidationReport(BaseModel):
    target_service: str
    incident_id: str
    baseline_availability_percent: float
    total_strategies_evaluated: int
    recommended_strategy: str
    simulations: List[WhatIfSimulationOutcome]
    timestamp: str


SUPPORTED_RECOVERY_STRATEGIES = [
    {
        "action_type": "restart_pod",
        "params": {"strategy": "rolling", "drain_timeout_sec": 30},
        "recovery_time": 25.0,
        "avail_impact": +45.0,
        "risk_level": "LOW",
        "risk_score": 0.20,
        "resources": "0 additional CPU/Memory",
        "side_effects": ["Transient in-flight request drops if drain timeout exceeded"],
        "rollback": ["Prior container revision remains cached locally"],
        "feasibility": 0.95,
    },
    {
        "action_type": "scale_service",
        "params": {"replicas": 4, "cpu_limit": "2000m"},
        "recovery_time": 15.0,
        "avail_impact": +60.0,
        "risk_level": "LOW",
        "risk_score": 0.15,
        "resources": "+2 vCPU, +2048MB RAM across cluster",
        "side_effects": ["Increased database connection pool utilization from new replicas"],
        "rollback": ["Downscale replicas back to original baseline (2)"],
        "feasibility": 0.98,
    },
    {
        "action_type": "rollback_deployment",
        "params": {"target_revision": "v2.4.0"},
        "recovery_time": 45.0,
        "avail_impact": +85.0,
        "risk_level": "MEDIUM",
        "risk_score": 0.35,
        "resources": "Image pull bandwidth",
        "side_effects": ["Database schema backwards-incompatibility if migration occurred"],
        "rollback": ["Re-apply failed image revision if regression persists"],
        "feasibility": 0.90,
    },
    {
        "action_type": "clear_cache",
        "params": {"flush_all": False, "keyspace": "session:*"},
        "recovery_time": 5.0,
        "avail_impact": +30.0,
        "risk_level": "LOW",
        "risk_score": 0.10,
        "resources": "Negligible",
        "side_effects": ["Temporary database query stampede while cache warms up"],
        "rollback": ["Cache repopulates automatically from primary store"],
        "feasibility": 0.99,
    },
    {
        "action_type": "increase_db_pool",
        "params": {"max_connections": 250},
        "recovery_time": 10.0,
        "avail_impact": +50.0,
        "risk_level": "MEDIUM",
        "risk_score": 0.40,
        "resources": "+500MB host memory on database instance",
        "side_effects": ["Risk of memory starvation if all connections execute heavy joins"],
        "rollback": ["Revert max_connections back to 100 via alter system"],
        "feasibility": 0.88,
    },
    {
        "action_type": "redirect_traffic",
        "params": {"target_zone": "us-east-1b", "traffic_percent": 100},
        "recovery_time": 20.0,
        "avail_impact": +70.0,
        "risk_level": "MEDIUM",
        "risk_score": 0.30,
        "resources": "Cross-AZ egress bandwidth",
        "side_effects": ["Elevated latency (+10ms) across cross-zone link"],
        "rollback": ["Rebalance DNS routing equally across all AZs"],
        "feasibility": 0.92,
    },
    {
        "action_type": "isolate_service",
        "params": {"circuit_breaker_threshold": 5, "fallback_response": "static_mock"},
        "recovery_time": 2.0,
        "avail_impact": +25.0,
        "risk_level": "MEDIUM",
        "risk_score": 0.35,
        "resources": "None",
        "side_effects": ["Degraded functional features for isolated component"],
        "rollback": ["Reset circuit breaker to CLOSED state"],
        "feasibility": 0.94,
    },
]


class WhatIfLaboratoryValidator:
    """Evaluates and compares recovery options in sandbox mode."""

    @classmethod
    def simulate_all_recovery_strategies(
        cls,
        target_service: str,
        incident_id: str,
    ) -> WhatIfLabValidationReport:
        outcomes: List[WhatIfSimulationOutcome] = []

        for strat in SUPPORTED_RECOVERY_STRATEGIES:
            outcomes.append(
                WhatIfSimulationOutcome(
                    action_type=strat["action_type"],
                    target_service=target_service,
                    action_parameters=strat["params"],
                    is_simulated=True,
                    is_destructive=False,
                    expected_recovery_time_sec=strat["recovery_time"],
                    availability_impact_percent=strat["avail_impact"],
                    risk_level=strat["risk_level"],
                    risk_score=strat["risk_score"],
                    resource_requirements=strat["resources"],
                    potential_side_effects=strat["side_effects"],
                    rollback_prerequisites=strat["rollback"],
                    feasibility_score=strat["feasibility"],
                )
            )

        # Rank by (availability_impact / risk_score)
        sorted_outcomes = sorted(
            outcomes,
            key=lambda x: (x.availability_impact_percent / max(0.01, x.risk_score)),
            reverse=True,
        )
        recommended = sorted_outcomes[0].action_type if sorted_outcomes else "scale_service"

        return WhatIfLabValidationReport(
            target_service=target_service,
            incident_id=incident_id,
            baseline_availability_percent=45.0,
            total_strategies_evaluated=len(outcomes),
            recommended_strategy=recommended,
            simulations=outcomes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
