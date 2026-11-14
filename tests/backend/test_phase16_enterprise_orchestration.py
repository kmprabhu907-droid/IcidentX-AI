"""
INCIDENTX AI - Phase 16 Comprehensive Test Suite (Hackathon Demonstration & Orchestration)
"""

import pytest
from backend.app.services.demonstration.schemas import DemonstrationScenarioID
from backend.app.services.demonstration.orchestration_engine import DemonstrationOrchestrator


@pytest.mark.asyncio
async def test_scenario_catalog():
    orchestrator = DemonstrationOrchestrator()
    scenarios = orchestrator.list_scenarios()
    assert len(scenarios) == 3
    ids = [s.scenario_id for s in scenarios]
    assert DemonstrationScenarioID.SCENARIO_A in ids
    assert DemonstrationScenarioID.SCENARIO_B in ids
    assert DemonstrationScenarioID.SCENARIO_C in ids


@pytest.mark.asyncio
async def test_end_to_end_orchestration_loop_scenario_a():
    """Validates the full 16-step autonomous SRE orchestration loop for Scenario A."""
    orchestrator = DemonstrationOrchestrator()
    result = await orchestrator.execute_scenario(
        scenario_id=DemonstrationScenarioID.SCENARIO_A,
        environment="DEMOMESH",
    )
    assert result.is_completed is True
    assert len(result.steps) == 16
    assert all(s.status.value == "COMPLETED" for s in result.steps)
    assert "Unindexed ledger transaction query" in result.root_cause_ruling
    assert result.confidence_score >= 0.90
    assert "Rollback" in result.remediation_executed
    assert result.postmortem_id is not None
    assert result.total_duration_seconds >= 0.0


@pytest.mark.asyncio
async def test_end_to_end_orchestration_loop_scenario_b():
    """Validates full loop for Scenario B (Kubernetes OOMKilled)."""
    orchestrator = DemonstrationOrchestrator()
    result = await orchestrator.execute_scenario(
        scenario_id=DemonstrationScenarioID.SCENARIO_B,
        environment="DEMOMESH",
    )
    assert result.is_completed is True
    assert len(result.steps) == 16
    assert "OOMKilled" in result.root_cause_ruling
    assert result.recovery_status == "RECOVERY_SUCCESSFUL"


@pytest.mark.asyncio
async def test_scenario_reset_and_history():
    orchestrator = DemonstrationOrchestrator()
    res = await orchestrator.execute_scenario(DemonstrationScenarioID.SCENARIO_C)
    history = orchestrator.list_executions()
    assert len(history) >= 1
    found = orchestrator.get_execution(res.execution_id)
    assert found is not None

    # Reset
    orchestrator.reset_scenarios()
    assert orchestrator._active_scenario_id is None
