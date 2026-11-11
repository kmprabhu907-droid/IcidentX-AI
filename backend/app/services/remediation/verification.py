"""
INCIDENTX AI - Recovery Verification Engine
Performs empirical before-and-after telemetry comparison across error rates,
P95 latencies, container metrics, and downstream dependency health.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional, Tuple


class TelemetryVerifier:
    """
    Evaluates recovery effectiveness by contrasting telemetry snapshots.
    Guarantees that no incident is marked resolved without empirical verification.
    """

    @staticmethod
    def compare_snapshots(
        service_name: str,
        before_snapshot_json: Optional[str],
        after_snapshot_json: Optional[str],
    ) -> Dict[str, Any]:
        """Produce a structured delta comparison between before and after telemetry snapshots."""
        try:
            before_dict = json.loads(before_snapshot_json) if before_snapshot_json else {}
        except Exception:
            before_dict = {}

        try:
            after_dict = json.loads(after_snapshot_json) if after_snapshot_json else {}
        except Exception:
            after_dict = {}

        before_svc = before_dict.get(service_name, {})
        after_svc = after_dict.get(service_name, {})

        err_before = float(before_svc.get("error_rate", 0.0))
        err_after = float(after_svc.get("error_rate", 0.0))
        p95_before = float(before_svc.get("latency_p95_ms", 0.0))
        p95_after = float(after_svc.get("latency_p95_ms", 0.0))
        cpu_before = float(before_svc.get("cpu_utilization", 0.0))
        cpu_after = float(after_svc.get("cpu_utilization", 0.0))
        mem_before = float(before_svc.get("memory_utilization", 0.0))
        mem_after = float(after_svc.get("memory_utilization", 0.0))
        pool_before = float(before_svc.get("db_pool_utilization", 0.0))
        pool_after = float(after_svc.get("db_pool_utilization", 0.0))
        health_before = before_svc.get("health_status", "UNKNOWN")
        health_after = after_svc.get("health_status", "UNKNOWN")

        delta_err = round(err_after - err_before, 2)
        delta_p95 = round(p95_after - p95_before, 2)
        delta_cpu = round(cpu_after - cpu_before, 2)
        delta_mem = round(mem_after - mem_before, 2)
        delta_pool = round(pool_after - pool_before, 2)

        is_improved = (delta_err < 0 or delta_p95 < -50.0 or delta_mem < -10.0 or delta_pool < -20.0)
        is_healthy = (health_after == "HEALTHY" and err_after <= 1.0)

        if is_healthy and is_improved:
            status = "VERIFIED"
        elif is_improved:
            status = "PARTIALLY_VERIFIED"
        elif delta_err > 0 or delta_p95 > 100.0:
            status = "FAILED"
        else:
            status = "INCONCLUSIVE"

        return {
            "service_name": service_name,
            "verification_status": status,
            "metrics": {
                "error_rate": {"before": err_before, "after": err_after, "delta": delta_err},
                "latency_p95_ms": {"before": p95_before, "after": p95_after, "delta": delta_p95},
                "cpu_utilization": {"before": cpu_before, "after": cpu_after, "delta": delta_cpu},
                "memory_utilization": {"before": mem_before, "after": mem_after, "delta": delta_mem},
                "db_pool_utilization": {"before": pool_before, "after": pool_after, "delta": delta_pool},
                "health_status": {"before": health_before, "after": health_after},
            },
            "is_recovery_confirmed": status == "VERIFIED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
