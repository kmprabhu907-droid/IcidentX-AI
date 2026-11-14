"""
INCIDENTX AI - DemoMesh Infrastructure Adapter (Phase 8.1)
Concrete implementation of BaseInfrastructureAdapter for the in-memory simulation engine.
Preserves full compatibility with Phase 0–7 continuous observability and benchmarks.
"""

from datetime import datetime, timezone
import time
from typing import List, Optional
from backend.app.infrastructure.core.base_adapter import BaseInfrastructureAdapter
from backend.app.infrastructure.core.infrastructure_models import (
    ConnectionStatus,
    EnvironmentHealth,
    EnvironmentMetadata,
    EnvironmentMode,
    InfrastructureEvent,
    InfrastructureService,
    InfrastructureWorkload,
    ResourceMetric,
    WorkloadStatus,
)
from backend.app.infrastructure.demomesh.demomesh_health import DemoMeshHealth
from backend.app.infrastructure.demomesh.demomesh_inventory import DemoMeshInventory
from backend.app.services.observability.demo_mesh import demo_mesh


class DemoMeshAdapter(BaseInfrastructureAdapter):
    """Infrastructure Adapter for DemoMesh Simulation Mode."""

    def __init__(self):
        self._connected: bool = True
        self._last_sync: str = datetime.now(timezone.utc).isoformat()

    @property
    def mode(self) -> EnvironmentMode:
        return EnvironmentMode.DEMOMESH

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_read_only(self) -> bool:
        return False

    @property
    def data_source(self) -> str:
        return "SIMULATED"

    async def connect(self) -> bool:
        if not demo_mesh._running:
            await demo_mesh.start()
        self._connected = True
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return True

    async def disconnect(self) -> None:
        # Do not terminate simulation background worker if benchmarks depend on it
        self._connected = False

    async def health_check(self) -> EnvironmentHealth:
        return DemoMeshHealth.evaluate_health()

    async def list_services(self) -> List[InfrastructureService]:
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return DemoMeshInventory.list_services()

    async def list_workloads(self, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        self._last_sync = datetime.now(timezone.utc).isoformat()
        return DemoMeshInventory.list_workloads(namespace=namespace)

    async def get_workload_status(
        self, workload_id: str, namespace: Optional[str] = None
    ) -> Optional[WorkloadStatus]:
        return DemoMeshInventory.get_workload_status(workload_id=workload_id)

    async def get_events(
        self, limit: int = 50, namespace: Optional[str] = None
    ) -> List[InfrastructureEvent]:
        events: List[InfrastructureEvent] = []
        logs = demo_mesh.get_logs(limit=limit)

        for i, log_entry in enumerate(logs):
            lvl = log_entry.get("level", "INFO")
            is_warn = lvl in ["WARN", "ERROR", "FATAL"]
            ev_type = "Warning" if is_warn else "Normal"
            svc = log_entry.get("service_name", "mesh")

            events.append(
                InfrastructureEvent(
                    id=f"sim-ev-{i}-{int(time.time())}",
                    event_type=ev_type,
                    reason="LogSignal" if not is_warn else "AnomalyDetected",
                    message=log_entry.get("message", "Simulated mesh event"),
                    source_component="demomesh-logger",
                    resource_kind="SimulatedContainer",
                    resource_name=svc,
                    namespace="demomesh-sim",
                    count=1,
                    first_timestamp=log_entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    last_timestamp=log_entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                )
            )

        # Append active fault events if present
        for svc_name, fault in demo_mesh.active_faults.items():
            events.append(
                InfrastructureEvent(
                    id=f"sim-fault-{svc_name}",
                    event_type="Warning",
                    reason="InjectedChaosFault",
                    message=f"Chaos fault injected on {svc_name}: {fault.get('type')}",
                    source_component="chaos-controller",
                    resource_kind="SimulatedContainer",
                    resource_name=svc_name,
                    namespace="demomesh-sim",
                    count=1,
                    first_timestamp=datetime.now(timezone.utc).isoformat(),
                    last_timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

        return events[:limit]

    async def get_resource_metrics(
        self, workload_id: Optional[str] = None
    ) -> List[ResourceMetric]:
        metrics_list: List[ResourceMetric] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        latest = demo_mesh.get_latest_metrics()

        for svc_name, m_dict in latest.items():
            if workload_id and workload_id not in [svc_name, f"sim-wl-{svc_name}"]:
                continue

            cpu_val = float(m_dict.get("cpu_utilization", 20.0))
            mem_val = float(m_dict.get("memory_utilization", 40.0))
            lat_val = float(m_dict.get("latency_p95_ms", 35.0))
            rps_val = float(m_dict.get("rps", 10.0))

            metrics_list.append(
                ResourceMetric(
                    workload_id=f"sim-wl-{svc_name}",
                    workload_name=svc_name,
                    namespace="demomesh-sim",
                    metric_name="cpu_utilization",
                    value=round(cpu_val, 2),
                    unit="percent",
                    timestamp=now_iso,
                    data_source="SIMULATED",
                )
            )
            metrics_list.append(
                ResourceMetric(
                    workload_id=f"sim-wl-{svc_name}",
                    workload_name=svc_name,
                    namespace="demomesh-sim",
                    metric_name="memory_utilization",
                    value=round(mem_val, 2),
                    unit="percent",
                    timestamp=now_iso,
                    data_source="SIMULATED",
                )
            )
            metrics_list.append(
                ResourceMetric(
                    workload_id=f"sim-wl-{svc_name}",
                    workload_name=svc_name,
                    namespace="demomesh-sim",
                    metric_name="latency_p95_ms",
                    value=round(lat_val, 2),
                    unit="ms",
                    timestamp=now_iso,
                    data_source="SIMULATED",
                )
            )
            metrics_list.append(
                ResourceMetric(
                    workload_id=f"sim-wl-{svc_name}",
                    workload_name=svc_name,
                    namespace="demomesh-sim",
                    metric_name="rps",
                    value=round(rps_val, 2),
                    unit="req/s",
                    timestamp=now_iso,
                    data_source="SIMULATED",
                )
            )

        return metrics_list

    async def get_environment_metadata(self) -> EnvironmentMetadata:
        services = DemoMeshInventory.list_services()
        workloads = DemoMeshInventory.list_workloads()
        health = DemoMeshHealth.evaluate_health()

        return EnvironmentMetadata(
            mode=EnvironmentMode.DEMOMESH,
            name="DemoMesh Simulation Engine",
            cluster_name="demomesh-simulation-v7",
            cluster_version="v7.4-simulation",
            api_endpoint="in-memory://demomesh.internal",
            version="v7.4-simulation",
            connection_status=ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.DISCONNECTED,
            is_read_only=False,  # Simulation allows chaos fault mutation
            is_simulated=True,
            data_source="SIMULATED",
            namespaces=["demomesh-sim"],
            namespace="demomesh-sim",
            node_count=1,
            total_services=len(services),
            total_workloads=len(workloads),
            last_sync_timestamp=self._last_sync,
            connection_error=None if self._connected else "Simulation disconnected",
        )
