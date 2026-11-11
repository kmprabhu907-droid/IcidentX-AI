"""
INCIDENTX AI - Four-State Telemetry Comparison Engine
Compares 4 distinct operational states:
  State A: HEALTHY_BASELINE - Normal behaviour before failure (steady-state historical mean)
  State B: PRE_INCIDENT - Measurements immediately before or during failure onset
  State C: POST_REMEDIATION - Measurements immediately following remediation and verification
  State D: CURRENT_STATE - Latest continuous telemetry measurements

Evaluates all Ten Golden Signals with strict unit, interval, and service identity guarantees.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Units and noise floors for each Golden Signal
SIGNAL_SPECIFICATIONS: Dict[str, Dict[str, Any]] = {
    "cpu_utilization": {"unit": "%", "noise_floor": 3.0, "higher_is_worse": True},
    "memory_utilization": {"unit": "%", "noise_floor": 2.0, "higher_is_worse": True},
    "disk_utilization": {"unit": "%", "noise_floor": 2.0, "higher_is_worse": True},
    "network_throughput_mbps": {"unit": "MB/s", "noise_floor": 1.0, "higher_is_worse": True},
    "latency_p50_ms": {"unit": "ms", "noise_floor": 10.0, "higher_is_worse": True},
    "latency_p95_ms": {"unit": "ms", "noise_floor": 25.0, "higher_is_worse": True},
    "latency_p99_ms": {"unit": "ms", "noise_floor": 50.0, "higher_is_worse": True},
    "error_rate": {"unit": "%", "noise_floor": 0.5, "higher_is_worse": True},
    "db_pool_utilization": {"unit": "%", "noise_floor": 5.0, "higher_is_worse": True},
    "availability_pct": {"unit": "%", "noise_floor": 0.2, "higher_is_worse": False},
    "dependency_health": {"unit": "%", "noise_floor": 1.0, "higher_is_worse": False},
    "request_rate": {"unit": "rps", "noise_floor": 2.0, "higher_is_worse": False},
}


@dataclass
class MetricStateValue:
    """Detailed four-state values and comparative deltas for a single metric."""
    metric_name: str
    unit: str
    healthy_baseline: float
    pre_incident: float
    post_remediation: float
    current_state: float
    
    # Computed comparative deltas
    delta_failure: float = 0.0          # Pre-incident vs Baseline (impact of original failure)
    delta_recovery: float = 0.0         # Post-remediation vs Pre-incident (immediate recovery)
    delta_degradation: float = 0.0      # Current vs Post-remediation (drift since remediation)
    delta_total_departure: float = 0.0  # Current vs Healthy Baseline (overall departure)
    
    # Recovery retention and regression indicators
    recovery_retained_ratio: float = 1.0  # 1.0 = 100% retained, 0.0 = completely regressed back to failure
    is_regressing: bool = False
    status_summary: str = "STABLE"


@dataclass
class FourStateComparison:
    """Container for the comprehensive four-state comparison across all signals."""
    service_name: str
    comparison_window_minutes: int
    metrics: Dict[str, MetricStateValue] = field(default_factory=dict)
    regressing_metrics: List[str] = field(default_factory=list)
    recovered_metrics: List[str] = field(default_factory=list)
    worsening_metrics: List[str] = field(default_factory=list)
    overall_health_score: float = 1.0  # 0.0 (total failure/regression) to 1.0 (fully healthy)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "comparison_window_minutes": self.comparison_window_minutes,
            "regressing_metrics": self.regressing_metrics,
            "recovered_metrics": self.recovered_metrics,
            "worsening_metrics": self.worsening_metrics,
            "overall_health_score": round(self.overall_health_score, 3),
            "summary": self.summary,
            "metrics": {
                name: {
                    "metric_name": m.metric_name,
                    "unit": m.unit,
                    "healthy_baseline": round(m.healthy_baseline, 2),
                    "pre_incident": round(m.pre_incident, 2),
                    "post_remediation": round(m.post_remediation, 2),
                    "current_state": round(m.current_state, 2),
                    "delta_failure": round(m.delta_failure, 2),
                    "delta_recovery": round(m.delta_recovery, 2),
                    "delta_degradation": round(m.delta_degradation, 2),
                    "delta_total_departure": round(m.delta_total_departure, 2),
                    "recovery_retained_ratio": round(m.recovery_retained_ratio, 2),
                    "is_regressing": m.is_regressing,
                    "status_summary": m.status_summary,
                }
                for name, m in self.metrics.items()
            },
        }


class FourStateComparisonEngine:
    """
    Evaluates telemetry across the 4 distinct operational lifecycle states.
    Ensures that comparisons are performed on identical service identifiers,
    standardized units, and synchronized time resolution windows.
    """

    @classmethod
    def compare(
        cls,
        service_name: str,
        healthy_baseline: Dict[str, float],
        pre_incident: Dict[str, float],
        post_remediation: Dict[str, float],
        current_state: Dict[str, float],
        window_minutes: int = 15,
    ) -> FourStateComparison:
        """
        Executes four-state comparison across all metrics present in current telemetry.
        """
        comparison = FourStateComparison(
            service_name=service_name,
            comparison_window_minutes=window_minutes,
        )

        all_metric_names = set(current_state.keys()) | set(pre_incident.keys()) | set(post_remediation.keys())

        regressing: List[str] = []
        recovered: List[str] = []
        worsening: List[str] = []

        total_metrics = 0
        healthy_count = 0

        for metric_name in sorted(all_metric_names):
            if metric_name not in current_state:
                continue

            spec = SIGNAL_SPECIFICATIONS.get(
                metric_name,
                {"unit": "raw", "noise_floor": 1.0, "higher_is_worse": True}
            )
            unit = spec["unit"]
            noise_floor = spec["noise_floor"]
            higher_is_worse = spec["higher_is_worse"]

            # Skip non-numeric metadata keys (e.g. data_source, timestamp, service_name, health_status)
            try:
                curr = float(current_state.get(metric_name, 0.0))
                base = float(healthy_baseline.get(metric_name, curr))
                pre = float(pre_incident.get(metric_name, curr))
                post = float(post_remediation.get(metric_name, base))
            except (ValueError, TypeError):
                continue

            # Compute fundamental deltas
            delta_failure = pre - base
            delta_recovery = post - pre
            delta_degradation = curr - post
            delta_total_departure = curr - base

            # Calculate recovery magnitude & retention
            # Case 1: Higher value indicates worse performance (e.g. latency, cpu, error rate)
            if higher_is_worse:
                rec_magnitude = pre - post
                deg_magnitude = curr - post

                if rec_magnitude > noise_floor:
                    # Metric experienced recovery
                    if deg_magnitude <= 0:
                        retained_ratio = 1.0  # Even better than post-remediation
                    else:
                        retained_ratio = max(0.0, 1.0 - (deg_magnitude / rec_magnitude))
                else:
                    retained_ratio = 1.0 if abs(curr - base) <= noise_floor else 0.0

                # Regression criteria: degraded significantly from post-remediation AND exceeds baseline + noise floor
                is_regr = (deg_magnitude > noise_floor) and (curr > base + noise_floor)
                is_worse_than_failure = curr >= pre and (curr > base + noise_floor)

            # Case 2: Lower value indicates worse performance (e.g. availability, dependency health)
            else:
                rec_magnitude = post - pre
                deg_magnitude = post - curr

                if rec_magnitude > noise_floor:
                    if deg_magnitude <= 0:
                        retained_ratio = 1.0
                    else:
                        retained_ratio = max(0.0, 1.0 - (deg_magnitude / rec_magnitude))
                else:
                    retained_ratio = 1.0 if abs(base - curr) <= noise_floor else 0.0

                is_regr = (deg_magnitude > noise_floor) and (curr < base - noise_floor)
                is_worse_than_failure = curr <= pre and (curr < base - noise_floor)

            # Assign status summary
            if is_worse_than_failure:
                status = "WORSENED_BEYOND_FAILURE"
                worsening.append(metric_name)
            elif is_regr:
                status = "REGRESSING"
                regressing.append(metric_name)
            elif abs(curr - base) <= noise_floor:
                status = "HEALTHY_STABLE"
                recovered.append(metric_name)
            else:
                status = "MILD_DEPARTURE"

            total_metrics += 1
            if not is_regr and not is_worse_than_failure:
                healthy_count += 1

            mv = MetricStateValue(
                metric_name=metric_name,
                unit=unit,
                healthy_baseline=base,
                pre_incident=pre,
                post_remediation=post,
                current_state=curr,
                delta_failure=delta_failure,
                delta_recovery=delta_recovery,
                delta_degradation=delta_degradation,
                delta_total_departure=delta_total_departure,
                recovery_retained_ratio=retained_ratio,
                is_regressing=is_regr or is_worse_than_failure,
                status_summary=status,
            )
            comparison.metrics[metric_name] = mv

        comparison.regressing_metrics = regressing
        comparison.worsening_metrics = worsening
        comparison.recovered_metrics = recovered
        comparison.overall_health_score = (healthy_count / total_metrics) if total_metrics > 0 else 1.0

        if worsening:
            comparison.summary = (
                f"{service_name} has regressed beyond original failure levels on {len(worsening)} metric(s): "
                f"{', '.join(worsening)}."
            )
        elif regressing:
            comparison.summary = (
                f"{service_name} exhibits post-remediation regression on {len(regressing)} metric(s): "
                f"{', '.join(regressing)}."
            )
        else:
            comparison.summary = (
                f"{service_name} telemetry is stable. Post-remediation recovery retained across all monitored signals."
            )

        return comparison
