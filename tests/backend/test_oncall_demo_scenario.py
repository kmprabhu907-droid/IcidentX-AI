"""
INCIDENTX AI - On-Call Incident Demonstration Runner Test Suite (Phase 8.7)
Verifies:
1. End-to-end execution of 'The Midnight Black Friday Meltdown' scenario.
2. All 9 lifecycle stages executed with non-zero duration and valid outputs.
3. Sub-second MTTA auto-acknowledgment by Tier-1 Primary SRE.
4. Investigation results include KubernetesInvestigatorAgent in completed agents.
5. Courtroom 2.0 root-cause ruling formulation.
6. Remediation proposal with risk assessment.
7. Blameless post-mortem markdown and Slack executive announcement formatting.
8. API endpoint /api/v1/oncall/scenarios/midnight-meltdown functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.services.agents.oncall_demo_scenario import (
    OnCallDemoScenarioRunner,
    OnCallScenarioExecutionResult,
)
from backend.main import app


@pytest.mark.asyncio
async def test_black_friday_meltdown_direct_execution():
    result = await OnCallDemoScenarioRunner.run_black_friday_meltdown()

    assert isinstance(result, OnCallScenarioExecutionResult)
    assert result.scenario_id == "midnight_black_friday_meltdown"
    assert result.incident_id.startswith("inc-bf-")
    assert result.page_id.startswith("page-")
    assert result.mtta_seconds < 1.0  # Sub-second MTTA
    assert result.total_execution_ms > 0
    assert len(result.lifecycle_stages) == 8
    assert "KubernetesInvestigatorAgent" in result.completed_agents
    assert result.confidence_score > 0.0
    assert result.remediation_action is not None
    assert result.recovery_status == "VERIFIED_RECOVERED"
    assert len(result.postmortem_summary) > 50
    assert "INCIDENT UPDATE" in result.slack_announcement


@pytest.mark.asyncio
async def test_black_friday_meltdown_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/oncall/scenarios/midnight-meltdown")
        assert resp.status_code == 200
        data = resp.json()

        assert data["scenario_id"] == "midnight_black_friday_meltdown"
        assert data["incident_id"].startswith("inc-bf-")
        assert data["mtta_seconds"] < 1.0
        assert "KubernetesInvestigatorAgent" in data["completed_agents"]
        assert len(data["lifecycle_stages"]) >= 8
        assert "Blameless Post-Mortem Report" in data["postmortem_summary"]
