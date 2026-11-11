# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: Controlled Chaos & Fault Injection
# Validates Platform Resilience across 10 Distinct Infrastructure Failure Modes
# ==============================================================================

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.validation.chaos_validator import CHAOS_TEST_SUITE, ChaosTestingValidator


class TestPhase7ChaosAndFailureInjection:
    """Validates platform resilience under controlled synthetic failure injection."""

    def test_chaos_test_suite_covers_all_mandated_failure_modes(self):
        assert len(CHAOS_TEST_SUITE) == 10, "Chaos suite must cover 10 distinct failure modes"
        types = [c["fault_type"] for c in CHAOS_TEST_SUITE]
        assert "SERVICE_CRASH" in types
        assert "DELAYED_API_RESPONSE" in types
        assert "DB_CONNECTION_EXHAUSTION" in types
        assert "HIGH_CPU_STARVATION" in types
        assert "MEMORY_PRESSURE" in types
        assert "NETWORK_PACKET_LOSS" in types
        assert "DEPENDENCY_FAILURE" in types
        assert "INVALID_AGENT_OUTPUT" in types
        assert "AGENT_TIMEOUT" in types
        assert "TOOL_EXECUTION_FAILURE" in types

    @pytest.mark.asyncio
    async def test_run_full_chaos_testbed(self, db_session: AsyncSession):
        report = await ChaosTestingValidator.run_full_chaos_testbed(session=db_session)
        assert report.total_experiments == 10
        assert report.passed_experiments == 10
        assert report.failed_experiments == 0
        assert report.detection_rate_percent == 100.0
        assert report.safe_recovery_rate_percent == 100.0
        for exp in report.results:
            assert exp.detected_by_platform is True
            assert exp.safe_handling_verified is True
            assert exp.system_recovered is True
