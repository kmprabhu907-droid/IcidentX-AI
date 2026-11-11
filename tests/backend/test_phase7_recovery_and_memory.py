# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: Recovery Closed-Loop & Reliability Memory
# Validates 10-Step Lifecycle, Failure Backoff, and Memory Provenance Controls
# ==============================================================================

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.validation.memory_validator import ReliabilityMemoryValidator
from backend.app.services.validation.recovery_validator import AutonomousRecoveryValidator


class TestPhase7RecoveryAndMemoryValidation:
    """Validates autonomous recovery closed-loop and continuous reliability memory."""

    @pytest.mark.asyncio
    async def test_successful_10_step_recovery_lifecycle(self, db_session: AsyncSession):
        report = await AutonomousRecoveryValidator.validate_successful_recovery_loop(
            session=db_session, incident_id="inc-rec-success", service_name="payment-service"
        )
        assert report.lifecycle_completed_successfully is True
        assert report.recovery_outcome == "RESOLVED"
        assert report.verification_passed is True
        assert len(report.steps) == 10

        step_names = [s.step_name for s in report.steps]
        assert "INCIDENT_DETECTION" in step_names
        assert "INCIDENT_INVESTIGATION" in step_names
        assert "ROOT_CAUSE_IDENTIFICATION" in step_names
        assert "STRATEGY_GENERATION" in step_names
        assert "STRATEGY_COMPARISON" in step_names
        assert "SAFETY_RISK_EVALUATION" in step_names
        assert "APPROVAL_GATE" in step_names
        assert "AUTONOMOUS_EXECUTION" in step_names
        assert "RECOVERY_VERIFICATION" in step_names
        assert "PERSIST_RESULT_AND_LEARN" in step_names

    @pytest.mark.asyncio
    async def test_recovery_failure_halts_repeated_actions_and_escalates(self, db_session: AsyncSession):
        """Negative test: Verifies that a failed recovery stops repeated attempts and pages SRE."""
        fail_report = await AutonomousRecoveryValidator.validate_recovery_failure_and_escalation_loop(
            session=db_session, incident_id="inc-rec-fail", service_name="payment-service"
        )
        assert fail_report.lifecycle_completed_successfully is False
        assert fail_report.recovery_outcome == "ESCALATED_AFTER_FAILURE"
        assert fail_report.verification_passed is False
        assert fail_report.escalation_reason is not None

        # Check safety halt step
        step10 = fail_report.steps[-1]
        assert step10.step_name == "SAFETY_HALT_AND_ESCALATION"
        assert step10.status == "ESCALATED"
        assert step10.details["prevented_repeated_action"] is True

    @pytest.mark.asyncio
    async def test_reliability_memory_learning_and_provenance_controls(self, db_session: AsyncSession):
        mem_report = await ReliabilityMemoryValidator.validate_memory_learning(
            session=db_session, service_name="payment-service"
        )
        assert mem_report.total_memories_indexed >= 3
        assert mem_report.trusted_memories_count >= 2
        assert mem_report.unverified_quarantined_count >= 1
        assert mem_report.overall_memory_effectiveness_score >= 0.90

        # Verify that unconfirmed heuristic records are blocked from inference
        quarantine_test = mem_report.retrieval_tests[-1]
        assert quarantine_test.matched_memory_id is None
        assert quarantine_test.provenance_check_passed is True
