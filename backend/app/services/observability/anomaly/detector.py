"""
INCIDENTX AI - Unified Advanced Anomaly & Resource-Creep Detector
Evaluates microservice telemetry against dynamic baselines, EWMA trajectories,
linear trend slopes, and multi-signal correlation clusters.
Generates structured SRE diagnostics answering the 10 core investigation questions.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid

from backend.app.services.observability.anomaly.baseline import DynamicBaselineEngine, MetricBaseline
from backend.app.services.observability.anomaly.confidence import AnomalyConfidenceCalculator
from backend.app.services.observability.anomaly.ewma import EWMAEngine
from backend.app.services.observability.anomaly.rules import (
    CORRELATION_CLUSTERS,
    METRIC_CONSTRAINTS,
    AnomalySeverity,
    classify_anomaly_severity,
)
from backend.app.services.observability.anomaly.trend_analysis import ResourceCreepDetector


class AnomalyCandidate:
    """Represents a fully adjudicated anomaly detection finding."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        metric_name: str,
        observed_value: float,
        expected_baseline: float,
        deviation: float,
        ewma_value: float,
        trend_slope: Optional[float],
        severity: AnomalySeverity,
        confidence: float,
        detector_type: str,
        supporting_evidence: Dict[str, Any],
        explanation_10_questions: Dict[str, str],
        data_source: str = "SIMULATED",
    ):
        self.anomaly_id = str(uuid.uuid4())
        self.service_id = service_id
        self.service_name = service_name
        self.metric_name = metric_name
        self.observed_value = round(observed_value, 2)
        self.expected_baseline = round(expected_baseline, 2)
        self.deviation = round(deviation, 2)
        self.ewma_value = round(ewma_value, 2)
        self.trend_slope = round(trend_slope, 4) if trend_slope is not None else None
        self.severity = severity
        self.confidence = round(confidence, 2)
        self.detector_type = detector_type
        self.supporting_evidence = supporting_evidence
        self.explanation_10_questions = explanation_10_questions
        self.data_source = data_source
        self.detected_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "metric_name": self.metric_name,
            "observed_value": self.observed_value,
            "expected_baseline": self.expected_baseline,
            "deviation": self.deviation,
            "ewma_value": self.ewma_value,
            "trend_slope": self.trend_slope,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "detector_type": self.detector_type,
            "supporting_evidence": self.supporting_evidence,
            "explanation": self.explanation_10_questions,
            "data_source": self.data_source,
            "detected_at": self.detected_at.isoformat(),
        }


class UnifiedAnomalyDetector:
    """
    Coordinates baseline tracking, EWMA filtering, linear trend regression,
    multi-signal correlation, and confidence scoring across microservice telemetry.
    """

    def __init__(
        self,
        baseline_engine: Optional[DynamicBaselineEngine] = None,
        ewma_engine: Optional[EWMAEngine] = None,
        creep_detector: Optional[ResourceCreepDetector] = None,
    ):
        self.baseline_engine = baseline_engine or DynamicBaselineEngine(window_size=60, min_samples=10)
        self.ewma_engine = ewma_engine or EWMAEngine()
        self.creep_detector = creep_detector or ResourceCreepDetector(window_size=45, min_samples=10)

        # Track consecutive anomaly cycles: (service, metric) -> count
        self._consecutive_counts: Dict[tuple, int] = {}

    def evaluate_service_snapshot(
        self,
        service_id: str,
        service_name: str,
        current_metrics: Dict[str, Any],
        service_tier: str = "Tier-1",
    ) -> List[AnomalyCandidate]:
        """
        Evaluates point-in-time metrics for a microservice and returns verified anomaly candidates.
        """
        candidates: List[AnomalyCandidate] = []
        data_source = current_metrics.get("data_source", "SIMULATED")
        now = datetime.now(timezone.utc)

        # 1. First pass: Update baselines and trackers for each metric
        for m_name in METRIC_CONSTRAINTS.keys():
            val = current_metrics.get(m_name)
            if val is not None:
                # Update EWMA
                self.ewma_engine.update(service_name, m_name, val)
                # Update creep detector sliding window
                self.creep_detector.add_sample(service_name, m_name, val, timestamp=now)

        # 2. Second pass: Detect abnormal metrics
        abnormal_metrics: Dict[str, Dict[str, Any]] = {}

        for m_name in METRIC_CONSTRAINTS.keys():
            val = current_metrics.get(m_name)
            if val is None:
                continue

            try:
                val_f = float(val)
            except (ValueError, TypeError):
                continue

            baseline = self.baseline_engine.get_baseline(service_name, m_name)
            cfg = METRIC_CONSTRAINTS[m_name]
            min_noise_floor = 3.0 if "%" in cfg.get("unit", "") else (10.0 if "ms" in cfg.get("unit", "") else 1.0)
            std_dev = max(1.0, baseline.std_dev)
            deviation = val_f - baseline.mean
            z_score = abs(deviation) / std_dev

            # Check EWMA evaluation
            ewma_eval = self.ewma_engine.evaluate_deviation(
                service_name=service_name,
                metric_name=m_name,
                observed_value=val_f,
                baseline_mean=baseline.mean,
                baseline_std=std_dev,
            )

            # Check Resource Creep evaluation
            creep_eval = self.creep_detector.evaluate_creep(
                service_name=service_name,
                metric_name=m_name,
                current_value=val_f,
            )

            # Determine anomaly triggers
            crit_thresh = cfg.get("critical_threshold")
            warn_thresh = cfg.get("warn_threshold")
            inverted = m_name in ["availability_pct", "dependency_health"]

            threshold_breached = False
            if crit_thresh is not None:
                if (inverted and val_f <= crit_thresh) or (not inverted and val_f >= crit_thresh):
                    threshold_breached = True
            if warn_thresh is not None:
                if (inverted and val_f <= warn_thresh) or (not inverted and val_f >= warn_thresh):
                    threshold_breached = True

            is_stat_anomaly = (
                baseline.has_sufficient_history
                and abs(deviation) >= min_noise_floor
                and (z_score >= 3.0 or ewma_eval["is_sudden_spike"] or ewma_eval["is_sustained_shift"])
            )
            is_creep_anomaly = creep_eval is not None and creep_eval.get("is_creep", False)

            if is_stat_anomaly or is_creep_anomaly or threshold_breached:
                abnormal_metrics[m_name] = {
                    "val": val_f,
                    "baseline": baseline,
                    "z_score": z_score,
                    "deviation": deviation,
                    "ewma_eval": ewma_eval,
                    "creep_eval": creep_eval,
                    "is_creep": is_creep_anomaly,
                }
            else:
                # Normal sample: add to clean baseline to keep it adaptive
                self.baseline_engine.add_observation(service_name, m_name, val_f, is_known_anomaly=False)
                self._consecutive_counts[(service_name, m_name)] = 0

        # 3. Third pass: Multi-signal correlation & SRE diagnostic formulation
        for m_name, info in abnormal_metrics.items():
            key = (service_name, m_name)
            self._consecutive_counts[key] = self._consecutive_counts.get(key, 0) + 1
            consec = self._consecutive_counts[key]

            # Find corroborating signals within service using correlation clusters
            corroborating: List[str] = []
            cluster_name = ""
            cluster_explanation = ""
            for cluster in CORRELATION_CLUSTERS:
                if cluster["primary"] == m_name:
                    for corrob_metric in cluster["corroborating"]:
                        if corrob_metric in abnormal_metrics:
                            corroborating.append(corrob_metric)
                    if corroborating:
                        cluster_name = cluster["name"]
                        cluster_explanation = cluster["explanation"]

            # Calculate explainable confidence score
            creep_info = info["creep_eval"]
            r_squared = creep_info.get("r_squared") if creep_info else None
            conf_data = AnomalyConfidenceCalculator.calculate(
                z_score=info["z_score"],
                consecutive_observations=consec,
                baseline_std_dev=info["baseline"].std_dev,
                baseline_mean=info["baseline"].mean,
                trend_r_squared=r_squared,
                corroborating_signals_count=len(corroborating),
                sample_count=info["baseline"].sample_count,
            )

            # Classify severity
            severity = classify_anomaly_severity(
                metric_name=m_name,
                observed_value=info["val"],
                baseline_value=info["baseline"].mean,
                z_score=info["z_score"],
                is_creep=info["is_creep"],
                corroborating_count=len(corroborating),
                confidence=conf_data["confidence"],
                service_tier=service_tier,
            )

            # Determine detector type
            if info["is_creep"]:
                detector_type = "RESOURCE_CREEP_OLS"
            elif info["ewma_eval"]["is_sudden_spike"]:
                detector_type = "EWMA_SUDDEN_SPIKE"
            elif info["ewma_eval"]["is_sustained_shift"]:
                detector_type = "EWMA_SUSTAINED_SHIFT"
            elif info["z_score"] >= 3.0:
                detector_type = "DYNAMIC_BASELINE_3SIGMA"
            else:
                detector_type = "STATIC_THRESHOLD_BREACH"

            # Formulate explainable 10-Question SRE diagnostic
            diagnostics = self._answer_10_sre_questions(
                service_name=service_name,
                metric_name=m_name,
                observed_value=info["val"],
                baseline_mean=info["baseline"].mean,
                deviation=info["deviation"],
                consecutive_cycles=consec,
                corroborating=corroborating,
                cluster_explanation=cluster_explanation,
                confidence=conf_data["confidence"],
                creep_info=creep_info,
            )

            candidate = AnomalyCandidate(
                service_id=service_id,
                service_name=service_name,
                metric_name=m_name,
                observed_value=info["val"],
                expected_baseline=info["baseline"].mean,
                deviation=info["deviation"],
                ewma_value=info["ewma_eval"]["current_ewma"],
                trend_slope=creep_info.get("slope") if creep_info else None,
                severity=severity,
                confidence=conf_data["confidence"],
                detector_type=detector_type,
                supporting_evidence={
                    "z_score": round(info["z_score"], 2),
                    "baseline_std": info["baseline"].std_dev,
                    "confidence_breakdown": conf_data["components"],
                    "corroborating_signals": corroborating,
                    "cluster_name": cluster_name,
                    "cluster_explanation": cluster_explanation,
                    "creep_analysis": creep_info,
                },
                explanation_10_questions=diagnostics,
                data_source=data_source,
            )
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _answer_10_sre_questions(
        service_name: str,
        metric_name: str,
        observed_value: float,
        baseline_mean: float,
        deviation: float,
        consecutive_cycles: int,
        corroborating: List[str],
        cluster_explanation: str,
        confidence: float,
        creep_info: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Synthesizes deterministic answers to the 10 SRE diagnostic questions."""
        cfg = METRIC_CONSTRAINTS.get(metric_name, {})
        unit = cfg.get("unit", "")
        direction = "above" if deviation > 0 else "below"
        seconds_abnormal = consecutive_cycles * 5

        # Question 9: Projected impact
        if creep_info and creep_info.get("projected_tte_seconds"):
            tte_mins = round(creep_info["projected_tte_seconds"] / 60.0, 1)
            projected = f"Sustained creep at {creep_info['rate_per_minute']}{unit}/min will cross critical limits in ~{tte_mins} minutes."
        elif deviation > 0:
            projected = f"If persistent, will degrade caller SLA and induce cascading timeouts across {service_name} dependencies."
        else:
            projected = f"Declining metric threatens availability and throughput guarantees."

        # Question 10: Recommended investigation action
        if "memory" in metric_name:
            next_action = f"Inspect {service_name} heap profiles and active worker object allocations."
        elif "db_pool" in metric_name:
            next_action = f"Check active Postgres connection count and slow executing transaction locks."
        elif "latency" in metric_name:
            next_action = f"Analyze distributed trace waterfalls for {service_name} downstream RPC delays."
        elif "disk" in metric_name:
            next_action = f"Verify WAL log rotation, disk cache sizing, and partition free space on {service_name}."
        elif "error" in metric_name:
            next_action = f"Query correlated structured error logs filtered by trace_id."
        else:
            next_action = f"Inspect service telemetry and check recent deployment diffs."

        corrob_str = ", ".join(corroborating) if corroborating else "None (isolated signal)"
        if cluster_explanation:
            corrob_str += f" ({cluster_explanation})"

        return {
            "what_happened": f"Abnormal {metric_name} detected on {service_name}: observed {observed_value}{unit}.",
            "affected_service": service_name,
            "metric_changed": metric_name,
            "normal_baseline": f"{baseline_mean}{unit}",
            "deviation_magnitude": f"{abs(round(deviation, 2))}{unit} {direction} normal baseline ({abs(round((deviation / max(0.01, baseline_mean)) * 100, 1))}%)",
            "duration_abnormal": f"~{seconds_abnormal} seconds ({consecutive_cycles} consecutive collection ticks)",
            "corroborating_signals": corrob_str,
            "confidence_assessment": f"{round(confidence * 100, 1)}% confidence based on variance, persistence, and multi-signal evidence.",
            "projected_impact": projected,
            "next_investigation_step": next_action,
        }
