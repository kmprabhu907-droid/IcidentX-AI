# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: Hackathon Showcase & Scorecard API
# Validates Showcase Endpoints, Autonomous Loop Execution, and Pipeline Monitoring
# ==============================================================================

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestPhase7ShowcaseAPI:
    """Validates the Hackathon Showcase REST endpoints."""

    @pytest.mark.asyncio
    async def test_get_benchmark_scenarios(self, client: AsyncClient):
        resp = await client.get("/api/v1/showcase/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 15
        first = data[0]
        assert "scenario_id" in first
        assert "name" in first
        assert "ground_truth_root_cause" in first

    @pytest.mark.asyncio
    async def test_get_scenario_details(self, client: AsyncClient):
        resp = await client.get("/api/v1/showcase/scenarios/cpu_exhaustion")
        assert resp.status_code == 200
        sc = resp.json()
        assert sc["scenario_id"] == "cpu_exhaustion"
        assert sc["target_service"] == "payment-service"
        assert len(sc["hypotheses"]) >= 2

    @pytest.mark.asyncio
    async def test_get_scorecard(self, client: AsyncClient):
        resp = await client.get("/api/v1/showcase/scorecard")
        assert resp.status_code == 200
        card = resp.json()
        assert card["root_cause_accuracy_percent"] >= 90.0
        assert card["recovery_success_rate_percent"] >= 95.0
        assert card["mean_time_to_detect_ms"] < 50.0

    @pytest.mark.asyncio
    async def test_get_multi_agent_pipeline_validation(self, client: AsyncClient):
        resp = await client.get("/api/v1/showcase/multi-agent-pipeline?service=payment-service")
        assert resp.status_code == 200
        pipe = resp.json()
        assert pipe["total_agents_evaluated"] == 11
        assert pipe["successful_agents_count"] == 11
        assert len(pipe["information_flow_timeline"]) == 10

    @pytest.mark.asyncio
    async def test_launch_showcase_autonomous_loop(self, client: AsyncClient):
        payload = {
            "scenario_id": "cpu_exhaustion",
            "auto_approve_if_required": True,
        }
        resp = await client.post("/api/v1/showcase/launch", json=payload)
        assert resp.status_code == 200
        result = resp.json()
        assert result["scenario_id"] == "cpu_exhaustion"
        assert result["target_service"] == "payment-service"
        assert "courtroom" in result
        assert "what_if_lab" in result
        assert "recovery" in result
        assert "time_machine" in result
        assert result["recovery"]["lifecycle_completed_successfully"] is True
        assert len(result["recovery"]["steps"]) == 10
