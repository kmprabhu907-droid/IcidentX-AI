"""
INCIDENTX AI - Phase 13 Comprehensive Test Suite
Tests:
1. Advanced Recovery Verification (12 pillars & statuses)
2. Telemetry Comparison Engine (diffs, trends, honest missing baseline handling)
3. Recovery Regression Detection
4. Recovery Stability Engine (multi-interval observation & drift detection)
5. Automated Postmortem Generation (Facts vs AI, Markdown & HTML export)
6. Incident Knowledge Engine & Similarity Search
7. Recurring Failure Pattern Detection
8. Controlled Self-Learning & Safeguards (rejecting unverified hypotheses)
9. Versioned Learning Policy & Instant Rollback
10. Human Feedback & Continuous Improvement Recommendations
11. End-to-end Master Learning Service & API Integration
"""

import pytest
from datetime import datetime, timezone

from backend.app.services.learning.schemas import (
    MetricTrend,
    PostmortemTask,
    RecoveryCriteria,
    RecoveryStatus,
    TelemetryStage,
)
from backend.app.services.learning.telemetry_comparator import TelemetryComparator
from backend.app.services.learning.advanced_recovery_verifier import AdvancedRecoveryVerifier
from backend.app.services.learning.recovery_stability_engine import RecoveryStabilityEngine
from backend.app.services.learning.postmortem_generator import PostmortemGenerator
from backend.app.services.learning.incident_knowledge_engine import IncidentKnowledgeEngine
from backend.app.services.learning.self_learning_engine import ControlledSelfLearningEngine
from backend.app.services.learning.continuous_improvement_engine import ContinuousImprovementEngine
from backend.app.services.learning.learning_service import RecoveryAndLearningService


@pytest.mark.asyncio
async def test_telemetry_comparator_diff_and_trends():
    """Verifies before/after diff calculations, percentage changes, and health trends."""
    before = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-001",
        service_name="payment-service",
        stage=TelemetryStage.BEFORE,
        replicas_desired=2,
        replicas_ready=0,
        restart_count=8,
        error_rate_percent=38.5,
        p95_latency_ms=1850.0,
        cpu_percent=92.0,
        memory_percent=94.0,
    )
    after = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-001",
        service_name="payment-service",
        stage=TelemetryStage.AFTER,
        replicas_desired=2,
        replicas_ready=2,
        restart_count=0,
        error_rate_percent=0.15,
        p95_latency_ms=75.0,
        cpu_percent=28.0,
        memory_percent=42.0,
    )

    diff = TelemetryComparator.compare_snapshots(
        incident_id="INC-P13-001",
        service_name="payment-service",
        before=before,
        after=after,
    )

    assert diff.overall_trend == MetricTrend.IMPROVED
    assert diff.regression_detected is False
    assert len(diff.improved_metrics) >= 4
    assert diff.recovery_stability_score >= 0.8
    # Error rate improved
    err_diff = next(m for m in diff.metrics if m.metric_name == "http_5xx_error_rate")
    assert err_diff.trend == MetricTrend.IMPROVED
    assert err_diff.is_healthy is True
    assert err_diff.delta_value < 0  # dropped


@pytest.mark.asyncio
async def test_telemetry_comparator_missing_baseline_honesty():
    """Guarantees honesty: missing baselines are explicitly flagged without fabricating data."""
    after = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-002",
        service_name="order-service",
        stage=TelemetryStage.AFTER,
        replicas_desired=2,
        replicas_ready=2,
        error_rate_percent=0.5,
        p95_latency_ms=120.0,
    )

    # Before snapshot is None (missing baseline)
    diff = TelemetryComparator.compare_snapshots(
        incident_id="INC-P13-002",
        service_name="order-service",
        before=None,
        after=after,
    )

    assert diff.baseline_incomplete is True
    assert "entire_pre_remediation_baseline" in diff.missing_metrics
    # Trend should be UNKNOWN rather than fabricated IMPROVED
    err_diff = next(m for m in diff.metrics if m.metric_name == "http_5xx_error_rate")
    assert err_diff.trend == MetricTrend.UNKNOWN
    assert err_diff.baseline_present is False
    assert err_diff.delta_value is None


@pytest.mark.asyncio
async def test_advanced_recovery_verification_pillars():
    """Verifies that all 12 operational health pillars are evaluated before declaring RECOVERY_SUCCESSFUL."""
    before = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-003",
        service_name="payment-service",
        stage=TelemetryStage.BEFORE,
        error_rate_percent=25.0,
        p95_latency_ms=1200.0,
    )
    after = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-003",
        service_name="payment-service",
        stage=TelemetryStage.AFTER,
        replicas_desired=2,
        replicas_ready=2,
        restart_count=0,
        error_rate_percent=0.2,
        p95_latency_ms=80.0,
        cpu_percent=35.0,
        memory_percent=45.0,
        db_query_latency_ms=12.0,
        dependency_failure_rate_percent=0.0,
    )

    report = await AdvancedRecoveryVerifier.verify_service_recovery(
        incident_id="INC-P13-003",
        service_name="payment-service",
        before_snapshot=before,
        after_snapshot=after,
    )

    assert report.status == RecoveryStatus.RECOVERY_SUCCESSFUL
    assert report.pod_readiness_verified is True
    assert report.deployment_available is True
    assert report.restart_frequency_cleared is True
    assert report.error_rate_recovered is True
    assert report.latency_normalized is True
    assert report.resources_healthy is True
    assert report.database_healthy is True
    assert report.dependencies_healthy is True
    assert report.requires_escalation is False


@pytest.mark.asyncio
async def test_recovery_regression_detection():
    """Verifies that if remediation makes metrics worse, RECOVERY_REGRESSION is emitted and escalated."""
    before = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-004",
        service_name="auth-service",
        stage=TelemetryStage.BEFORE,
        error_rate_percent=5.0,
        p95_latency_ms=350.0,
    )
    # Remediation caused latency to spike to 2500ms and error rate to 45%
    after = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-004",
        service_name="auth-service",
        stage=TelemetryStage.AFTER,
        replicas_desired=2,
        replicas_ready=2,
        error_rate_percent=45.0,
        p95_latency_ms=2500.0,
    )

    report = await AdvancedRecoveryVerifier.verify_service_recovery(
        incident_id="INC-P13-004",
        service_name="auth-service",
        before_snapshot=before,
        after_snapshot=after,
    )

    assert report.status == RecoveryStatus.RECOVERY_REGRESSION
    assert report.requires_escalation is True
    assert len(report.failing_reasons) > 0


@pytest.mark.asyncio
async def test_recovery_stability_multi_window():
    """Verifies multi-interval observation window and drift detection."""
    # 1. Normal stable series
    stable_series = RecoveryStabilityEngine.generate_observation_series(
        incident_id="INC-P13-005",
        service_name="payment-service",
        initial_error_rate=0.1,
        initial_p95_latency=70.0,
        num_intervals=5,
        simulate_regression=False,
    )
    report_stable = RecoveryStabilityEngine.evaluate_stability(
        incident_id="INC-P13-005",
        service_name="payment-service",
        checks=stable_series,
        observation_window_seconds=300,
    )
    assert report_stable.is_stable is True
    assert report_stable.status == RecoveryStatus.RECOVERY_SUCCESSFUL
    assert report_stable.stability_confidence >= 0.85

    # 2. Regressing series with drift
    regressed_series = RecoveryStabilityEngine.generate_observation_series(
        incident_id="INC-P13-005",
        service_name="payment-service",
        initial_error_rate=0.1,
        initial_p95_latency=70.0,
        num_intervals=5,
        simulate_regression=True,
    )
    report_regressed = RecoveryStabilityEngine.evaluate_stability(
        incident_id="INC-P13-005",
        service_name="payment-service",
        checks=regressed_series,
        observation_window_seconds=300,
    )
    assert report_regressed.is_stable is False
    assert report_regressed.status == RecoveryStatus.RECOVERY_REGRESSION
    assert report_regressed.escalation_triggered is True


@pytest.mark.asyncio
async def test_postmortem_generator_facts_vs_ai_and_exports():
    """Verifies that postmortem generator separates facts from AI interpretations and outputs valid Markdown & HTML."""
    now = datetime.now(timezone.utc)
    pm = PostmortemGenerator.generate_postmortem(
        incident_id="INC-P13-006",
        title="Payment Service Memory Leak Outage",
        severity="SEV-1",
        environment="PRODUCTION",
        affected_services=["payment-service"],
        detected_at=now,
        acknowledged_at=now,
        remediated_at=now,
        resolved_at=now,
        verified_root_cause="Unbounded transaction cache caused JVM heap exhaustion.",
        root_cause_is_conclusive=True,
        remediation_performed="Rolled back deployment to revision 12",
        verified_facts=["HTTP 5xx rate spiked to 38.2%", "Pods restarted with OOMKilled code 137"],
        ai_interpretations=["Hypothesis Agent correlated memory ramp with commit sha-88f"],
    )

    assert pm.postmortem_id.startswith("postm-")
    assert pm.root_cause_is_conclusive is True
    assert len(pm.verified_facts) == 2
    assert len(pm.ai_interpretations) == 1
    # Check Markdown formatting
    assert "# INCIDENT POSTMORTEM:" in pm.markdown_content
    assert "[FACT]" in pm.markdown_content
    assert "[AI]" in pm.markdown_content
    # Check HTML formatting
    assert "<!DOCTYPE html>" in pm.html_content
    assert "class=\"badge badge-fact\"" in pm.html_content
    assert "class=\"badge badge-ai\"" in pm.html_content


@pytest.mark.asyncio
async def test_incident_knowledge_similarity_and_patterns():
    """Verifies historical knowledge base similarity search and recurring pattern detection."""
    ke = IncidentKnowledgeEngine()
    
    # Search similar incident for payment memory leak
    matches = ke.search_similar(
        service_name="payment-service",
        error_signature="OutOfMemoryError: Java heap space",
        query_text="heap exhaustion memory leak",
    )
    assert len(matches) > 0
    top = matches[0]
    assert top.similarity_score > 0.5
    assert "payment-service" in top.common_services
    assert "k8s-rollback-deployment" in top.recommended_remediations

    # Recurring pattern detection
    patterns = ke.detect_recurring_patterns(min_occurrences=1)
    assert len(patterns) > 0


@pytest.mark.asyncio
async def test_controlled_self_learning_safeguard_rejection():
    """SAFEGUARD: Verifies engine rejects unverified or low-confidence AI conclusions (<0.75)."""
    learner = ControlledSelfLearningEngine()
    active_before = learner.get_active_policy().version_id

    # Attempt to train on unverified hypothesis with 0.40 confidence
    policy = learner.learn_from_incident(
        incident_id="INC-P13-007",
        verified_root_cause_category="UNVERIFIED_CORRELATION",
        is_verified=False,
        confidence_score=0.40,
        successful_remediations=[],
        failed_remediations=[],
        human_approved=False,
    )

    # Must be rejected (returns None)
    assert policy is None
    # Active policy version must not have changed
    assert learner.get_active_policy().version_id == active_before


@pytest.mark.asyncio
async def test_controlled_self_learning_versioning_and_rollback():
    """Verifies versioned policy creation and instant rollback capability."""
    learner = ControlledSelfLearningEngine()
    base_ver = learner.get_active_policy().version_id

    # Learn from verified incident
    new_pol = learner.learn_from_incident(
        incident_id="INC-P13-008",
        verified_root_cause_category="MEMORY_LEAK",
        is_verified=True,
        confidence_score=0.95,
        successful_remediations=["k8s-rollback-deployment"],
        failed_remediations=[],
        human_approved=True,
        approved_by="sre-lead",
    )

    assert new_pol is not None
    assert new_pol.is_active is True
    assert learner.get_active_policy().version_id == new_pol.version_id
    assert new_pol.hypothesis_ranking_weights.get("MEMORY_LEAK") > 1.0

    # Instant Rollback
    rolled_back = learner.rollback_to_version(base_ver, rolled_back_by="sre-lead")
    assert rolled_back is True
    assert learner.get_active_policy().version_id == base_ver


@pytest.mark.asyncio
async def test_continuous_improvement_recommendations():
    """Verifies continuous improvement engine generates actionable, prioritized recommendations."""
    now = datetime.now(timezone.utc)
    pm = PostmortemGenerator.generate_postmortem(
        incident_id="INC-P13-009",
        title="Order Service Connection Pool Exhaustion",
        severity="SEV-2",
        environment="PRODUCTION",
        affected_services=["order-service"],
        detected_at=now,
        verified_root_cause="Database connection pool starvation due to slow unindexed query.",
        root_cause_is_conclusive=True,
    )

    recs = ContinuousImprovementEngine.generate_recommendations(
        incident_id="INC-P13-009",
        service_name="order-service",
        postmortem=pm,
    )

    assert len(recs) >= 1
    circuit_rec = next((r for r in recs if "Circuit Breaker" in r.title or "pool" in r.description.lower()), None)
    assert circuit_rec is not None
    assert circuit_rec.priority in ("P1", "P2")
    assert circuit_rec.suggested_owner != ""
    assert circuit_rec.verification_criteria != ""


@pytest.mark.asyncio
async def test_master_learning_service_end_to_end():
    """Verifies end-to-end integration across Master Learning Service."""
    service = RecoveryAndLearningService()
    now = datetime.now(timezone.utc)

    # 1. Record snapshots
    before = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-E2E",
        service_name="payment-service",
        stage=TelemetryStage.BEFORE,
        error_rate_percent=32.0,
        p95_latency_ms=1400.0,
    )
    after = TelemetryComparator.create_snapshot(
        incident_id="INC-P13-E2E",
        service_name="payment-service",
        stage=TelemetryStage.AFTER,
        replicas_desired=2,
        replicas_ready=2,
        error_rate_percent=0.1,
        p95_latency_ms=65.0,
        cpu_percent=30.0,
        memory_percent=40.0,
    )
    service.record_snapshot(before)
    service.record_snapshot(after)

    # 2. Verify Recovery
    rec_report = await service.verify_recovery(
        incident_id="INC-P13-E2E",
        service_name="payment-service",
        before_snapshot=before,
        after_snapshot=after,
    )
    assert rec_report.status == RecoveryStatus.RECOVERY_SUCCESSFUL

    # 3. Check Stability
    stab_report = service.check_stability(
        incident_id="INC-P13-E2E",
        service_name="payment-service",
    )
    assert stab_report.is_stable is True

    # 4. Generate Postmortem
    pm = service.generate_postmortem(
        incident_id="INC-P13-E2E",
        title="Payment Service Memory Pressure",
        severity="SEV-1",
        environment="DEMOMESH",
        affected_services=["payment-service"],
        detected_at=now,
        verified_root_cause="Unbounded memory cache caused container evictions.",
        root_cause_is_conclusive=True,
        remediation_performed="Rolled back deployment",
    )
    assert pm.postmortem_id.startswith("postm-")

    # 5. Continuous Improvement Recommendations
    recs = service.get_recommendations("INC-P13-E2E")
    assert len(recs) >= 1

    # 6. Submit Human Feedback
    fb = service.submit_human_feedback(
        incident_id="INC-P13-E2E",
        reviewer="oncall-lead",
        rating=5,
        comments="Root cause was 100% accurate; remediation resolved outage.",
    )
    assert fb.rating == 5
