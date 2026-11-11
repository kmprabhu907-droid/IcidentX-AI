# ==============================================================================
# IncidentX AI — Phase 7 Test Suite: Root Cause Intelligence & Courtroom Evaluation
# Validates Ground-Truth Matching, Evidence Balance, What-If Lab, and Time Machine
# ==============================================================================

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.benchmarks.root_cause_evaluator import RootCauseAccuracyEvaluator
from backend.app.services.validation.courtroom_validator import CourtroomValidator
from backend.app.services.validation.time_machine_validator import IncidentTimeMachineValidator
from backend.app.services.validation.what_if_validator import WhatIfLaboratoryValidator


class TestPhase7RootCauseAndInvestigationEvaluation:
    """Validates root cause accuracy, courtroom evidence balance, and simulation."""

    @pytest.mark.asyncio
    async def test_root_cause_accuracy_benchmark(self, db_session: AsyncSession):
        # Run across 3 core representative scenarios for fast automated test execution
        report = await RootCauseAccuracyEvaluator.run_accuracy_benchmark(
            session=db_session,
            scenario_ids=["cpu_exhaustion", "memory_leak", "db_connection_exhaustion"],
            organization_id="test-eval-org",
        )
        assert report.total_scenarios_evaluated == 3
        assert report.correct_identifications_count >= 2
        assert report.root_cause_accuracy_percentage >= 66.0
        assert report.average_evidence_relevance_score > 0.50
        assert report.brier_calibration_error < 0.25  # Well calibrated
        assert len(report.evaluations) == 3

    @pytest.mark.asyncio
    async def test_courtroom_evidence_balance_validation(self, db_session: AsyncSession):
        courtroom = await CourtroomValidator.validate_incident_courtroom(
            session=db_session, incident_id="inc-test-courtroom", service_name="payment-service"
        )
        assert courtroom.total_hypotheses_evaluated >= 2
        assert courtroom.winning_hypothesis_title != ""
        assert courtroom.confidence_margin > 0.0
        assert courtroom.unresolved_uncertainty_score < 0.50
        assert "confidence" in courtroom.verdict_justification.lower()
        assert len(courtroom.hypotheses) >= 2

    def test_what_if_laboratory_simulation_comparison(self):
        report = WhatIfLaboratoryValidator.simulate_all_recovery_strategies(
            target_service="payment-service", incident_id="inc-test-what-if"
        )
        assert report.total_strategies_evaluated == 7
        assert report.recommended_strategy in ["scale_service", "clear_cache", "restart_pod"]
        for sim in report.simulations:
            assert sim.is_simulated is True
            assert sim.is_destructive is False
            assert sim.expected_recovery_time_sec > 0
            assert sim.feasibility_score > 0.80

    @pytest.mark.asyncio
    async def test_incident_time_machine_validation(self, db_session: AsyncSession):
        tm_report = await IncidentTimeMachineValidator.validate_time_machine(
            session=db_session, incident_id="inc-test-tm", service_name="payment-service"
        )
        assert tm_report.total_timeline_events >= 8
        assert tm_report.reconstruction_fidelity_score >= 0.95
        assert len(tm_report.condition_comparisons) == 3
        for comp in tm_report.condition_comparisons:
            assert comp.status == "RECOVERED"
            assert comp.percentage_recovered >= 99.0
