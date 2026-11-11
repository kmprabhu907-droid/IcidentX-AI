"""
INCIDENTX AI - Remediation Effectiveness & Long-Term Stability Analysis
Connects Phase 4 remediation execution records with continuous telemetry
to assess whether interventions provided sustained recovery, temporary relief,
or secondary cascading degradation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.services.observability.regression.comparison_engine import SIGNAL_SPECIFICATIONS


@dataclass
class RemediationEffectivenessReport:
    """Outcome and stability analysis of a remediation action."""
    action_id: str
    action_name: str
    target_service_name: str
    outcome: str  # SUSTAINED_SUCCESS, TEMPORARY_SUCCESS, PARTIAL_SUCCESS, FAILED, REGRESSION_DETECTED, INSUFFICIENT_EVIDENCE
    stability_score: float  # 0.0 to 1.0
    immediate_verification_status: str  # VERIFIED, PARTIALLY_VERIFIED, FAILED, PENDING
    time_to_degradation_seconds: Optional[float] = None
    re_abnormal_metrics: List[str] = field(default_factory=list)
    secondary_degraded_metrics: List[str] = field(default_factory=list)
    required_rollback: bool = False
    observation_window_minutes: int = 15
    sample_count: int = 0
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_name": self.action_name,
            "target_service_name": self.target_service_name,
            "outcome": self.outcome,
            "stability_score": round(self.stability_score, 3),
            "immediate_verification_status": self.immediate_verification_status,
            "time_to_degradation_seconds": self.time_to_degradation_seconds,
            "re_abnormal_metrics": self.re_abnormal_metrics,
            "secondary_degraded_metrics": self.secondary_degraded_metrics,
            "required_rollback": self.required_rollback,
            "observation_window_minutes": self.observation_window_minutes,
            "sample_count": self.sample_count,
            "explanation": self.explanation,
        }


class RemediationEffectivenessAnalyzer:
    """
    Evaluates Phase 4 recovery interventions across long-term telemetry observations.
    """

    @classmethod
    def evaluate(
        cls,
        action_dict: Dict[str, Any],
        historical_samples: List[Dict[str, Any]],
        current_telemetry: Dict[str, float],
        healthy_baseline: Dict[str, float],
        target_metric: Optional[str] = None,
    ) -> RemediationEffectivenessReport:
        action_id = action_dict.get("id", action_dict.get("action_id", "act-unknown"))
        action_name = action_dict.get("name", "Unknown Remediation")
        target_service = action_dict.get("target_service_name", "unknown-service")
        verif_status = action_dict.get("verification_status", "PENDING")
        rollback_status = action_dict.get("rollback_status", "NONE")
        required_rollback = rollback_status in ["EXECUTING", "ROLLED_BACK", "ROLLBACK_FAILED"]

        # 1. Check if execution failed or verification failed immediately
        exec_status = action_dict.get("status", "PROPOSED")
        if exec_status == "FAILED" or verif_status == "FAILED":
            return RemediationEffectivenessReport(
                action_id=action_id,
                action_name=action_name,
                target_service_name=target_service,
                outcome="FAILED",
                stability_score=0.0,
                immediate_verification_status=verif_status,
                required_rollback=required_rollback,
                explanation=f"Remediation '{action_name}' failed during execution or immediate verification.",
            )

        # 2. Check observation sample sufficiency
        sample_count = len(historical_samples)
        if sample_count < 3 and not current_telemetry:
            return RemediationEffectivenessReport(
                action_id=action_id,
                action_name=action_name,
                target_service_name=target_service,
                outcome="INSUFFICIENT_EVIDENCE",
                stability_score=0.5,
                immediate_verification_status=verif_status,
                sample_count=sample_count,
                required_rollback=required_rollback,
                explanation=f"Insufficient post-remediation observations ({sample_count} samples). Minimum 3 required.",
            )

        # 3. Analyze whether the target metric or secondary metrics deteriorated
        re_abnormal: List[str] = []
        secondary: List[str] = []

        # Identify all monitored metrics on the service
        metrics_to_check = set(current_telemetry.keys()) | set(healthy_baseline.keys())
        healthy_cycles = 0
        total_eval_cycles = max(1, sample_count + 1)

        # Time to degradation tracking
        degradation_timestamp: Optional[datetime] = None
        executed_at_str = action_dict.get("executed_at")
        executed_at: Optional[datetime] = None
        if executed_at_str:
            try:
                executed_at = datetime.fromisoformat(executed_at_str.replace("Z", "+00:00"))
            except Exception:
                pass

        for metric in metrics_to_check:
            spec = SIGNAL_SPECIFICATIONS.get(metric, {"noise_floor": 2.0, "higher_is_worse": True})
            base = healthy_baseline.get(metric, 0.0)
            curr = current_telemetry.get(metric, base)
            floor = spec["noise_floor"]
            higher_worse = spec["higher_is_worse"]

            is_abnormal = False
            if higher_worse:
                if curr > (base + floor):
                    is_abnormal = True
            else:
                if curr < (base - floor):
                    is_abnormal = True

            if is_abnormal:
                if target_metric and metric == target_metric:
                    re_abnormal.append(metric)
                elif not target_metric and metric in ["latency_p95_ms", "error_rate", "db_pool_utilization", "cpu_utilization", "memory_utilization"]:
                    re_abnormal.append(metric)
                else:
                    secondary.append(metric)

        # 4. Check historical sample progression for temporary success
        consecutive_clean_cycles = 0
        observed_re_spike = False

        for sample in historical_samples:
            sample_time = sample.get("timestamp") or sample.get("bucket_start")
            is_sample_clean = True
            for m in (re_abnormal or [target_metric] if target_metric else []):
                val = sample.get(m, sample.get("average", 0.0))
                b_val = healthy_baseline.get(m, 0.0)
                fl = SIGNAL_SPECIFICATIONS.get(m, {}).get("noise_floor", 2.0)
                if val > (b_val + fl):
                    is_sample_clean = False
                    observed_re_spike = True
                    if not degradation_timestamp and sample_time:
                        try:
                            degradation_timestamp = datetime.fromisoformat(str(sample_time).replace("Z", "+00:00"))
                        except Exception:
                            pass
                    break

            if is_sample_clean:
                consecutive_clean_cycles += 1

        # Calculate time to degradation in seconds
        time_to_deg: Optional[float] = None
        if degradation_timestamp and executed_at:
            delta_sec = (degradation_timestamp - executed_at).total_seconds()
            if delta_sec > 0:
                time_to_deg = delta_sec

        # 5. Classify outcome
        if required_rollback:
            outcome = "FAILED"
            stability = 0.0
            explanation = f"Action '{action_name}' required rollback due to operational failure."
        elif re_abnormal:
            if consecutive_clean_cycles >= 2 or verif_status == "VERIFIED":
                outcome = "TEMPORARY_SUCCESS"
                stability = 0.35
                explanation = (
                    f"Remediation provided temporary recovery, but primary metric(s) [{', '.join(re_abnormal)}] "
                    f"degraded back to abnormal levels."
                )
            else:
                outcome = "REGRESSION_DETECTED"
                stability = 0.20
                explanation = (
                    f"Persistent failure detected. Monitored signal [{', '.join(re_abnormal)}] "
                    f"exceeds nominal baseline."
                )
        elif secondary:
            outcome = "PARTIAL_SUCCESS"
            stability = 0.65
            explanation = (
                f"Target service recovered, but secondary metric(s) [{', '.join(secondary)}] "
                f"exhibit degraded performance."
            )
        else:
            outcome = "SUSTAINED_SUCCESS"
            stability = 0.95
            explanation = (
                f"Remediation '{action_name}' achieved sustained recovery with all signals remaining within nominal baseline."
            )

        return RemediationEffectivenessReport(
            action_id=action_id,
            action_name=action_name,
            target_service_name=target_service,
            outcome=outcome,
            stability_score=stability,
            immediate_verification_status=verif_status,
            time_to_degradation_seconds=time_to_deg,
            re_abnormal_metrics=re_abnormal,
            secondary_degraded_metrics=secondary,
            required_rollback=required_rollback,
            sample_count=sample_count,
            explanation=explanation,
        )
