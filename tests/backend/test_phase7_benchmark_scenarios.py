# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: 15 Realistic Benchmark Scenarios
# Validates Scenario Library Completeness, Ground-Truth Definitions, and Execution
# ==============================================================================

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.benchmarks.scenarios import (
    BENCHMARK_SCENARIOS_LIBRARY,
    get_scenario,
    list_all_scenarios,
)
from backend.app.services.benchmarks.scenario_runner import BenchmarkScenarioRunner


class TestPhase7BenchmarkScenarios:
    """Validates the 15 realistic incident scenarios and benchmark execution."""

    def test_all_15_scenarios_exist_and_conform_to_schema(self):
        assert len(BENCHMARK_SCENARIOS_LIBRARY) == 15, "Scenario library must contain exactly 15 realistic scenarios"

        required_ids = [
            "cpu_exhaustion",
            "memory_leak",
            "db_connection_exhaustion",
            "api_latency_spike",
            "network_packet_loss",
            "service_dependency_failure",
            "deployment_induced_outage",
            "database_deadlock",
            "traffic_overload",
            "cascading_microservice_failure",
            "auth_service_failure",
            "disk_exhaustion",
            "cache_failure",
            "simultaneous_incidents",
            "ambiguous_incident",
        ]

        for sc_id in required_ids:
            sc = get_scenario(sc_id)
            assert sc is not None, f"Scenario '{sc_id}' must exist"
            assert sc.scenario_id == sc_id
            assert len(sc.name) > 5
            assert sc.severity in ["SEV-1", "SEV-2", "SEV-3"]
            assert len(sc.initial_conditions) >= 1
            assert len(sc.metric_evidence) >= 1
            assert len(sc.log_evidence) >= 1
            assert len(sc.timeline) >= 1
            assert len(sc.hypotheses) >= 1
            assert any(h.is_ground_truth for h in sc.hypotheses), f"Scenario '{sc_id}' must have a ground-truth hypothesis"
            assert sc.ground_truth_root_cause != ""
            assert sc.remediation.recommended_action != ""
            assert sc.verification.metric_to_check != ""

    def test_list_all_scenarios_metadata_export(self):
        sc_list = list_all_scenarios()
        assert len(sc_list) == 15
        for item in sc_list:
            assert "scenario_id" in item
            assert "ground_truth_root_cause" in item
            assert "recommended_action" in item

    @pytest.mark.asyncio
    async def test_scenario_runner_executes_single_scenario(self, db_session: AsyncSession):
        """Validates that BenchmarkScenarioRunner executes through real analytical pipeline."""
        res = await BenchmarkScenarioRunner.run_scenario(
            session=db_session, scenario_id="cpu_exhaustion", organization_id="test-bench-org"
        )
        assert res.scenario_id == "cpu_exhaustion"
        assert res.target_service == "payment-service"
        assert res.status in ["PASSED", "DEGRADED"]
        assert res.execution_duration_ms > 0
        assert res.collected_evidence_count >= 1
        assert res.hypotheses_evaluated >= 1
        assert res.confidence_score > 0.0
