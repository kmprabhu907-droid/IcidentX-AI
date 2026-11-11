# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: Multi-Agent Validation Engine
# Validates All 11 Designated Autonomous Agents and Inter-Agent Information Flow
# ==============================================================================

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.validation.multi_agent_validator import (
    AGENT_CATALOG,
    MultiAgentValidationHarness,
)


class TestPhase7MultiAgentValidation:
    """Validates the 11-agent architecture and information flow timeline."""

    def test_all_11_agents_registered_in_catalog(self):
        expected_agents = [
            "detection_agent",
            "classification_agent",
            "investigation_agent",
            "root_cause_analysis_agent",
            "evidence_verification_agent",
            "what_if_simulation_agent",
            "remediation_planning_agent",
            "safety_approval_agent",
            "recovery_execution_agent",
            "recovery_verification_agent",
            "reliability_memory_agent",
        ]
        assert len(AGENT_CATALOG) == 11, "Agent catalog must contain all 11 required agents"
        for ag_id in expected_agents:
            assert ag_id in AGENT_CATALOG, f"Agent '{ag_id}' must be registered"
            spec = AGENT_CATALOG[ag_id]
            assert len(spec.responsibilities) > 10
            assert len(spec.input_contract) > 5
            assert len(spec.output_contract) > 5

    @pytest.mark.asyncio
    async def test_validate_individual_agents(self, db_session: AsyncSession):
        context = {"service_name": "payment-service"}

        # Test detection agent
        det_report = await MultiAgentValidationHarness.validate_agent(db_session, "detection_agent", context)
        assert det_report.status == "SUCCESS"
        assert det_report.confidence_score is not None
        assert det_report.execution_duration_ms > 0

        # Test safety approval agent
        safe_report = await MultiAgentValidationHarness.validate_agent(db_session, "safety_approval_agent", context)
        assert safe_report.status == "SUCCESS"
        assert len(safe_report.evidence_tracked) >= 1

    @pytest.mark.asyncio
    async def test_validate_entire_11_agent_pipeline(self, db_session: AsyncSession):
        result = await MultiAgentValidationHarness.validate_entire_pipeline(
            session=db_session, service_name="payment-service"
        )
        assert result.total_agents_evaluated == 11
        assert result.successful_agents_count == 11
        assert result.failed_agents_count == 0
        assert result.overall_health == "FULLY_OPERATIONAL"
        assert len(result.agent_reports) == 11
        assert len(result.information_flow_timeline) == 10  # 10 handoffs between 11 agents
        assert result.total_pipeline_duration_ms > 0
