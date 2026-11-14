"""
INCIDENTX AI - Kubernetes Health Prober (Phase 8.1)
Inspects API server responsiveness, version endpoints, and control plane readiness.
"""

from datetime import datetime, timezone
import time
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMode,
)
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient


class KubernetesHealth:
    """Probes connectivity, version, and control plane status for Kubernetes."""

    def __init__(self, client: KubernetesClient):
        self.client = client

    async def evaluate_health(self) -> EnvironmentHealth:
        t0 = time.perf_counter()
        try:
            version_data = await self.client.get_version()
            git_ver = version_data.get("gitVersion", "v1.30.0")
            ns_list = await self.client.list_namespaces()

            now_iso = datetime.now(timezone.utc).isoformat()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return EnvironmentHealth(
                status="HEALTHY",
                mode=EnvironmentMode.KUBERNETES,
                latency_ms=latency_ms,
                is_healthy=True,
                active_incidents_or_faults=0,
                data_source="LIVE_K8S",
                details={
                    "cluster_version": git_ver,
                    "platform": version_data.get("platform", "linux/amd64"),
                    "namespaces_count": len(ns_list),
                    "namespaces": ns_list[:5],
                    "read_only": True,
                },
                checked_at=now_iso,
                last_checked_at=now_iso,
            )
        except Exception as e:
            now_iso = datetime.now(timezone.utc).isoformat()
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return EnvironmentHealth(
                status="UNHEALTHY",
                mode=EnvironmentMode.KUBERNETES,
                latency_ms=latency_ms,
                is_healthy=False,
                error_message=str(e),
                data_source="LIVE_K8S",
                details={"error": str(e), "read_only": True},
                checked_at=now_iso,
                last_checked_at=now_iso,
            )
