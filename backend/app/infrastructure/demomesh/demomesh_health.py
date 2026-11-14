"""
INCIDENTX AI - DemoMesh Health & Diagnostics (Phase 8.1)
Inspects active faults, metric degradation, and overall simulation mesh availability.
"""

from datetime import datetime, timezone
import time
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMode,
)
from backend.app.services.observability.demo_mesh import demo_mesh


class DemoMeshHealth:
    """Evaluates real-time health of the in-memory DemoMesh simulation."""

    @classmethod
    def evaluate_health(cls) -> EnvironmentHealth:
        t0 = time.perf_counter()
        fault_count = len(demo_mesh.active_faults)
        latest = demo_mesh.get_latest_metrics()
        services_count = len(latest)

        status = "HEALTHY"
        if fault_count >= 2:
            status = "UNHEALTHY"
        elif fault_count == 1:
            status = "DEGRADED"

        now_iso = datetime.now(timezone.utc).isoformat()
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return EnvironmentHealth(
            status=status,
            mode=EnvironmentMode.DEMOMESH,
            latency_ms=latency_ms,
            is_healthy=status in ["HEALTHY", "DEGRADED"],
            active_incidents_or_faults=fault_count,
            data_source="SIMULATED",
            details={
                "simulation_running": demo_mesh._running,
                "active_faults_count": fault_count,
                "active_faults": list(demo_mesh.active_faults.keys()),
                "services_count": services_count,
                "total_traces_buffered": len(demo_mesh.traces),
                "total_logs_buffered": len(demo_mesh.logs),
            },
            checked_at=now_iso,
            last_checked_at=now_iso,
        )
