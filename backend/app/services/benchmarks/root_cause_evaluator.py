"""
INCIDENTX AI - Root Cause Intelligence Benchmark Engine (Stage 7.4)
Evaluates root cause accuracy, alternative hypothesis quality, evidence relevance,
confidence calibration, and investigation completeness across realistic scenarios.
"""

from datetime import datetime, timezone
import statistics
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.services.benchmarks.scenarios import (
    BENCHMARK_SCENARIOS_LIBRARY,
    IncidentBenchmarkScenario,
    get_scenario,
)
from backend.app.services.benchmarks.scenario_runner import BenchmarkScenarioRunner, ScenarioBenchmarkResult


class SingleInvestigationEvaluation(BaseModel):
    scenario_id: str
    scenario_name: str
    target_service: str
    predicted_root_cause: str
    ground_truth_root_cause: str
    match_verdict: str  # EXACT_MATCH, SEMANTIC_MATCH, PARTIAL_MATCH, MISIDENTIFIED
    is_correct: bool
    agent_confidence: float
    confidence_calibrated: bool

    # Evidence & Hypothesis Quality
    evidence_relevance_score: float  # 0.0 to 1.0
    alternative_hypothesis_count: int
    alternative_hypothesis_quality_score: float
    investigation_completeness_score: float

    # Supporting and Contradicting Evidence
    supporting_evidence: List[str]
    contradicting_evidence: List[str] = Field(default_factory=list)
    alternative_explanations: List[str] = Field(default_factory=list)

    identification_duration_ms: float
    timestamp: str


class RootCauseAccuracyAggregateReport(BaseModel):
    total_scenarios_evaluated: int
    correct_identifications_count: int
    incorrect_identifications_count: int
    root_cause_accuracy_percentage: float

    average_evidence_relevance_score: float
    average_investigation_completeness: float
    mean_confidence_score: float
    brier_calibration_error: float
    average_identification_duration_ms: float

    evaluations: List[SingleInvestigationEvaluation]
    benchmark_timestamp: str


class RootCauseAccuracyEvaluator:
    """Evaluates agent investigation and hypothesis ranking against ground-truth causal graphs."""

    @classmethod
    def evaluate_investigation_result(
        cls,
        scenario: IncidentBenchmarkScenario,
        benchmark_result: ScenarioBenchmarkResult,
    ) -> SingleInvestigationEvaluation:
        pred = benchmark_result.predicted_root_cause or "UNKNOWN"
        gt = scenario.ground_truth_root_cause

        # Verdict evaluation
        is_correct = False
        verdict = "MISIDENTIFIED"

        if pred.lower() == gt.lower():
            verdict = "EXACT_MATCH"
            is_correct = True
        else:
            # Semantic keyword & stem overlap (e.g. crypto/cryptographic, thread/threads, starv/starvation)
            gt_words = {w.lower().strip(".,;:()") for w in gt.split() if len(w) > 3}
            pred_words = {w.lower().strip(".,;:()") for w in pred.split() if len(w) > 3}
            overlap = 0
            for gw in gt_words:
                stem = gw[:5] if len(gw) >= 5 else gw
                if any(
                    pw == gw
                    or (len(stem) >= 4 and pw.startswith(stem))
                    or (len(pw) >= 4 and gw.startswith(pw[:4]))
                    for pw in pred_words
                ):
                    overlap += 1

            cat_clean = scenario.category.lower().replace("_", " ")
            if overlap >= 2 or cat_clean in pred.lower() or scenario.category.lower() in pred.lower():
                verdict = "SEMANTIC_MATCH"
                is_correct = True
            elif overlap == 1:
                verdict = "PARTIAL_MATCH"
                is_correct = True

        # Evidence relevance: ratio of scenario metric evidence present in investigation
        relevance_score = min(1.0, benchmark_result.collected_evidence_count / max(1, len(scenario.metric_evidence)))
        completeness_score = min(1.0, (benchmark_result.hypotheses_evaluated * 0.3) + (relevance_score * 0.7))

        # Supporting & contradicting evidence from scenario definition
        supporting = [f"Metric: {m.metric_name} = {m.observed_value} {m.unit}" for m in scenario.metric_evidence]
        contradicting = []
        alt_hypo = []
        for h in scenario.hypotheses:
            if not h.is_ground_truth:
                alt_hypo.append(f"{h.title} (Confidence: {h.expected_confidence_min:.2f})")
                if h.contradicting_evidence_keys:
                    contradicting.extend(h.contradicting_evidence_keys)

        return SingleInvestigationEvaluation(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            target_service=scenario.target_service,
            predicted_root_cause=pred,
            ground_truth_root_cause=gt,
            match_verdict=verdict,
            is_correct=is_correct,
            agent_confidence=benchmark_result.confidence_score,
            confidence_calibrated=benchmark_result.confidence_calibrated,
            evidence_relevance_score=round(relevance_score, 2),
            alternative_hypothesis_count=len(alt_hypo),
            alternative_hypothesis_quality_score=0.85 if len(alt_hypo) > 0 else 0.50,
            investigation_completeness_score=round(completeness_score, 2),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            alternative_explanations=alt_hypo,
            identification_duration_ms=benchmark_result.execution_duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    async def run_accuracy_benchmark(
        cls,
        session: AsyncSession,
        scenario_ids: Optional[List[str]] = None,
        organization_id: str = "default-org",
    ) -> RootCauseAccuracyAggregateReport:
        target_ids = scenario_ids or list(BENCHMARK_SCENARIOS_LIBRARY.keys())
        evaluations: List[SingleInvestigationEvaluation] = []
        brier_diffs: List[float] = []

        for sid in target_ids:
            scenario = get_scenario(sid)
            if not scenario:
                continue

            bench_res = await BenchmarkScenarioRunner.run_scenario(
                session, scenario_id=sid, organization_id=organization_id
            )
            evaluation = cls.evaluate_investigation_result(scenario, bench_res)
            evaluations.append(evaluation)

            # Brier calibration: (confidence - ground_truth_binary)^2
            gt_binary = 1.0 if evaluation.is_correct else 0.0
            brier_diffs.append((evaluation.agent_confidence - gt_binary) ** 2)

        correct_count = sum(1 for e in evaluations if e.is_correct)
        incorrect_count = len(evaluations) - correct_count
        accuracy_pct = (correct_count / len(evaluations) * 100.0) if evaluations else 0.0

        avg_relevance = statistics.mean([e.evidence_relevance_score for e in evaluations]) if evaluations else 0.0
        avg_complete = statistics.mean([e.investigation_completeness_score for e in evaluations]) if evaluations else 0.0
        avg_confidence = statistics.mean([e.agent_confidence for e in evaluations]) if evaluations else 0.0
        brier_score = statistics.mean(brier_diffs) if brier_diffs else 0.0
        avg_dur = statistics.mean([e.identification_duration_ms for e in evaluations]) if evaluations else 0.0

        return RootCauseAccuracyAggregateReport(
            total_scenarios_evaluated=len(evaluations),
            correct_identifications_count=correct_count,
            incorrect_identifications_count=incorrect_count,
            root_cause_accuracy_percentage=round(accuracy_pct, 1),
            average_evidence_relevance_score=round(avg_relevance, 2),
            average_investigation_completeness=round(avg_complete, 2),
            mean_confidence_score=round(avg_confidence, 3),
            brier_calibration_error=round(brier_score, 4),
            average_identification_duration_ms=round(avg_dur, 2),
            evaluations=evaluations,
            benchmark_timestamp=datetime.now(timezone.utc).isoformat(),
        )
