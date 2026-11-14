"""
INCIDENTX AI - Telemetry Comparison Engine (Phase 13 Module 13.2)
Compares before, during, and after remediation snapshots across 10+ dimensions.
Detects regressions, evaluates recovery stability, and honestly flags missing baselines.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.learning.schemas import (
    MetricTrend,
    TelemetryComparisonReport,
    TelemetryMetricDiff,
    TelemetrySnapshot,
    TelemetryStage,
)


class TelemetryComparator:
    """
    Evaluates telemetry changes pre- and post-remediation.
    Honesty guarantee: Missing baselines are surfaced; measurements are never fabricated.
    """

    @classmethod
    def compare_snapshots(
        cls,
        incident_id: str,
        service_name: str,
        before: Optional[TelemetrySnapshot],
        after: Optional[TelemetrySnapshot],
        during: Optional[TelemetrySnapshot] = None,
        environment: str = "DEMOMESH",
    ) -> TelemetryComparisonReport:
        """
        Calculates diffs across all telemetry dimensions between before, during, and after.
        """
        comp_id = f"comp-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        
        diffs: List[TelemetryMetricDiff] = []
        missing_metrics: List[str] = []
        regressed_metrics: List[str] = []
        improved_metrics: List[str] = []
        unchanged_metrics: List[str] = []
        
        baseline_incomplete = before is None
        if before is None:
            missing_metrics.append("entire_pre_remediation_baseline")

        # Dimension Definitions: (name, unit, attr_name, lower_is_better, healthy_threshold)
        dimensions = [
            ("http_5xx_error_rate", "%", "error_rate_percent", True, 2.0),
            ("p95_latency", "ms", "p95_latency_ms", True, 300.0),
            ("p99_latency", "ms", "p99_latency_ms", True, 800.0),
            ("pod_readiness_ratio", "ratio", "pod_readiness_ratio", False, 1.0),
            ("pod_restart_count", "restarts", "restart_count", True, 0.0),
            ("cpu_utilization", "%", "cpu_percent", True, 80.0),
            ("memory_utilization", "%", "memory_percent", True, 80.0),
            ("throughput", "rps", "throughput_rps", False, 10.0),
            ("database_query_latency", "ms", "db_query_latency_ms", True, 50.0),
            ("network_drop_rate", "%", "network_drop_rate_percent", True, 0.5),
        ]

        healthy_count = 0
        total_evaluated = 0

        for name, unit, attr, lower_is_better, threshold in dimensions:
            b_val = getattr(before, attr, None) if before else None
            d_val = getattr(during, attr, None) if during else None
            a_val = getattr(after, attr, None) if after else None

            if a_val is None:
                missing_metrics.append(name)
                diffs.append(
                    TelemetryMetricDiff(
                        metric_name=name,
                        unit=unit,
                        before_value=b_val,
                        during_value=d_val,
                        after_value=None,
                        trend=MetricTrend.UNKNOWN,
                        threshold=threshold,
                        is_healthy=False,
                        baseline_present=b_val is not None,
                        evaluation_notes="Post-remediation measurement not available.",
                    )
                )
                continue

            total_evaluated += 1
            delta = None
            pct_change = None
            trend = MetricTrend.UNCHANGED
            
            # Check Health
            if lower_is_better:
                is_healthy = a_val <= threshold
            else:
                is_healthy = a_val >= threshold

            if is_healthy:
                healthy_count += 1

            # Trend against baseline
            if b_val is not None:
                delta = round(a_val - b_val, 3)
                if abs(b_val) > 0.0001:
                    pct_change = round(((a_val - b_val) / b_val) * 100.0, 2)
                else:
                    pct_change = 0.0 if delta == 0 else 100.0

                if abs(delta) < 0.001:
                    trend = MetricTrend.UNCHANGED
                    unchanged_metrics.append(name)
                elif lower_is_better:
                    if a_val < b_val:
                        trend = MetricTrend.IMPROVED
                        improved_metrics.append(name)
                    else:
                        trend = MetricTrend.REGRESSED
                        regressed_metrics.append(name)
                else:  # higher is better
                    if a_val > b_val:
                        trend = MetricTrend.IMPROVED
                        improved_metrics.append(name)
                    else:
                        trend = MetricTrend.REGRESSED
                        regressed_metrics.append(name)
            else:
                trend = MetricTrend.UNKNOWN
                missing_metrics.append(f"{name}_baseline")

            note = (
                f"Value: {a_val}{unit} (Threshold: {threshold}{unit}). "
                f"Trend: {trend.value}."
            )
            if delta is not None:
                note += f" Delta: {delta:+}{unit} ({pct_change:+}%)."

            diffs.append(
                TelemetryMetricDiff(
                    metric_name=name,
                    unit=unit,
                    before_value=b_val,
                    during_value=d_val,
                    after_value=a_val,
                    delta_value=delta,
                    percentage_change=pct_change,
                    trend=trend,
                    threshold=threshold,
                    is_healthy=is_healthy,
                    baseline_present=b_val is not None,
                    evaluation_notes=note,
                )
            )

        # Recovery Stability Score (0.0 to 1.0)
        stability_score = round(healthy_count / max(1, total_evaluated), 2)
        regression_detected = len(regressed_metrics) > 0

        # Overall Trend
        if regression_detected:
            overall_trend = MetricTrend.REGRESSED
        elif len(improved_metrics) > len(unchanged_metrics):
            overall_trend = MetricTrend.IMPROVED
        elif len(improved_metrics) > 0:
            overall_trend = MetricTrend.IMPROVED
        else:
            overall_trend = MetricTrend.UNCHANGED

        summary = (
            f"Telemetry comparison evaluated {total_evaluated} dimensions for '{service_name}'. "
            f"Improved: {len(improved_metrics)}, Regressed: {len(regressed_metrics)}, "
            f"Unchanged: {len(unchanged_metrics)}. Stability score: {stability_score*100:.0f}%."
        )
        if regression_detected:
            summary += f" REGRESSION DETECTED on metrics: {', '.join(regressed_metrics)}."
        if baseline_incomplete or len(missing_metrics) > 0:
            summary += f" Note: Telemetry baseline incomplete for {len(missing_metrics)} metric(s)."

        logger.info(f"[TelemetryComparator] Incident {incident_id} evaluated: {overall_trend.value}")

        return TelemetryComparisonReport(
            comparison_id=comp_id,
            incident_id=incident_id,
            service_name=service_name,
            environment=environment,
            evaluated_at=now,
            metrics=diffs,
            overall_trend=overall_trend,
            regression_detected=regression_detected,
            regressed_metrics=regressed_metrics,
            improved_metrics=improved_metrics,
            unchanged_metrics=unchanged_metrics,
            baseline_incomplete=baseline_incomplete or len(missing_metrics) > 0,
            missing_metrics=missing_metrics,
            recovery_stability_score=stability_score,
            summary=summary,
        )

    @classmethod
    def create_snapshot(
        cls,
        incident_id: str,
        service_name: str,
        stage: TelemetryStage,
        environment: str = "DEMOMESH",
        replicas_desired: int = 2,
        replicas_ready: int = 2,
        restart_count: int = 0,
        error_rate_percent: Optional[float] = None,
        p95_latency_ms: Optional[float] = None,
        p99_latency_ms: Optional[float] = None,
        throughput_rps: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        memory_percent: Optional[float] = None,
        db_query_latency_ms: Optional[float] = None,
        db_pool_utilization_percent: Optional[float] = None,
        dependency_failure_rate_percent: Optional[float] = None,
        network_drop_rate_percent: Optional[float] = None,
        is_simulated: bool = True,
        raw_metrics: Optional[Dict[str, Any]] = None,
    ) -> TelemetrySnapshot:
        """Helper to create a well-typed telemetry snapshot."""
        pod_ratio = round(replicas_ready / max(1, replicas_desired), 2)
        return TelemetrySnapshot(
            snapshot_id=f"snap-{uuid.uuid4().hex[:10]}",
            incident_id=incident_id,
            service_name=service_name,
            environment=environment,
            stage=stage,
            replicas_desired=replicas_desired,
            replicas_ready=replicas_ready,
            restart_count=restart_count,
            pod_readiness_ratio=pod_ratio,
            error_rate_percent=error_rate_percent,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            throughput_rps=throughput_rps,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            db_query_latency_ms=db_query_latency_ms,
            db_pool_utilization_percent=db_pool_utilization_percent,
            dependency_failure_rate_percent=dependency_failure_rate_percent,
            network_drop_rate_percent=network_drop_rate_percent,
            is_simulated=is_simulated,
            raw_metrics=raw_metrics or {},
        )
