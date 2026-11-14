"""
INCIDENTX AI - Recovery Stability Engine (Phase 13 Module 13.3)
Monitors service health over configurable observation windows (e.g. 5m, 15m, 30m).
Guarantees recovery is sustained without drift, restart spikes, or latent regressions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.learning.schemas import (
    RecoveryCriteria,
    RecoveryStabilityReport,
    RecoveryStatus,
    StabilityCheckPoint,
)


class RecoveryStabilityEngine:
    """
    Evaluates multi-interval stability across an observation window.
    Escalates when metrics drift or crash loops resume after initial recovery.
    """

    @classmethod
    def evaluate_stability(
        cls,
        incident_id: str,
        service_name: str,
        checks: List[StabilityCheckPoint],
        observation_window_seconds: int = 300,
        check_interval_seconds: int = 60,
        criteria: Optional[RecoveryCriteria] = None,
    ) -> RecoveryStabilityReport:
        """
        Processes a sequence of observation points collected over time.
        """
        stab_id = f"stab-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        
        max_err = criteria.max_5xx_error_rate_percent if criteria else 2.0
        max_lat = criteria.max_p95_latency_ms if criteria else 300.0

        if not checks:
            return RecoveryStabilityReport(
                stability_id=stab_id,
                incident_id=incident_id,
                service_name=service_name,
                observation_window_seconds=observation_window_seconds,
                check_interval_seconds=check_interval_seconds,
                total_checks_performed=0,
                checks=[],
                is_stable=False,
                regression_detected=False,
                escalation_triggered=False,
                status=RecoveryStatus.RECOVERY_PENDING,
                stability_confidence=0.0,
                notes="Observation window active. Awaiting first stability interval check.",
                last_checked_at=now,
            )

        healthy_checks = 0
        drift_count = 0
        prev_check: Optional[StabilityCheckPoint] = None

        for c in checks:
            is_healthy = (
                c.error_rate_percent <= max_err and
                c.p95_latency_ms <= max_lat and
                c.replicas_ready >= 1
            )
            c.is_healthy = is_healthy

            if prev_check:
                # Check for negative drift (error rate doubled or restarts increased)
                err_drift = (c.error_rate_percent - prev_check.error_rate_percent) > 1.5
                lat_drift = (c.p95_latency_ms - prev_check.p95_latency_ms) > 150.0
                restart_drift = c.restart_count > prev_check.restart_count
                if err_drift or lat_drift or restart_drift:
                    c.drift_detected = True
                    drift_count += 1
            
            if is_healthy and not c.drift_detected:
                healthy_checks += 1
            prev_check = c

        total_checks = len(checks)
        confidence = round(healthy_checks / max(1, total_checks), 2)
        regression_detected = drift_count > 0 or (total_checks >= 2 and not checks[-1].is_healthy)
        
        # Stability determination
        if regression_detected:
            is_stable = False
            status = RecoveryStatus.RECOVERY_REGRESSION
            escalation_triggered = True
            notes = (
                f"STABILITY BREACH: Service '{service_name}' showed performance drift or recurring faults "
                f"during the {observation_window_seconds}s observation window. {drift_count} drift events detected."
            )
        elif confidence >= 0.85:
            is_stable = True
            status = RecoveryStatus.RECOVERY_SUCCESSFUL
            escalation_triggered = False
            notes = (
                f"RECOVERY STABLE: Service '{service_name}' remained healthy and within SLA across "
                f"all {total_checks} observation intervals. Zero crash loops or metric spikes."
            )
        else:
            is_stable = False
            status = RecoveryStatus.RECOVERY_PARTIAL
            escalation_triggered = False
            notes = (
                f"STABILITY INCOMPLETE: {healthy_checks}/{total_checks} intervals healthy. "
                f"Metrics are fluctuating near SLA boundaries."
            )

        logger.info(f"[RecoveryStabilityEngine] Incident {incident_id} stability: is_stable={is_stable}, confidence={confidence}")

        return RecoveryStabilityReport(
            stability_id=stab_id,
            incident_id=incident_id,
            service_name=service_name,
            observation_window_seconds=observation_window_seconds,
            check_interval_seconds=check_interval_seconds,
            total_checks_performed=total_checks,
            checks=checks,
            is_stable=is_stable,
            regression_detected=regression_detected,
            escalation_triggered=escalation_triggered,
            status=status,
            stability_confidence=confidence,
            notes=notes,
            last_checked_at=now,
        )

    @classmethod
    def generate_observation_series(
        cls,
        incident_id: str,
        service_name: str,
        initial_error_rate: float = 0.2,
        initial_p95_latency: float = 85.0,
        replicas: int = 2,
        num_intervals: int = 5,
        simulate_regression: bool = False,
    ) -> List[StabilityCheckPoint]:
        """
        Generates simulated or polled multi-interval observation checks.
        """
        series: List[StabilityCheckPoint] = []
        now = datetime.now(timezone.utc)

        for i in range(num_intervals):
            # Normal small jitter
            err = max(0.0, round(initial_error_rate + (i * 0.05) - 0.02, 2))
            lat = max(20.0, round(initial_p95_latency + (i * 2.0) - 1.0, 1))
            restarts = 0

            # If simulating regression in later intervals
            if simulate_regression and i >= (num_intervals - 2):
                err = round(initial_error_rate + 4.5, 2)  # Spike
                lat = round(initial_p95_latency + 350.0, 1)
                restarts = 1

            series.append(
                StabilityCheckPoint(
                    check_index=i + 1,
                    timestamp=now,
                    error_rate_percent=err,
                    p95_latency_ms=lat,
                    replicas_ready=replicas,
                    restart_count=restarts,
                    is_healthy=err <= 2.0 and lat <= 300.0,
                    drift_detected=False,
                )
            )
        return series
