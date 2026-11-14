"""
INCIDENTX AI - DemoMesh Inventory Mapper (Phase 8.1)
Extracts and maps in-memory simulated services and container workloads into
standardized InfrastructureService and InfrastructureWorkload models.
"""

from typing import List, Optional
from backend.app.infrastructure.core.infrastructure_models import (
    InfrastructureService,
    InfrastructureWorkload,
    WorkloadPhase,
    WorkloadStatus,
)
from backend.app.services.observability.demo_mesh import demo_mesh


class DemoMeshInventory:
    """Discovers simulated services and workloads from DemoMesh."""

    @classmethod
    def list_services(cls) -> List[InfrastructureService]:
        """Maps DemoMesh service definitions to InfrastructureService."""
        services = []
        for name, meta in demo_mesh.SERVICE_DEFINITIONS.items():
            svc_type = "ClusterIP" if meta.get("type") == "service" else ("LoadBalancer" if meta.get("type") == "gateway" else "Headless")
            ports = [
                {"name": "http", "port": 8080 if "gateway" in name else 8000, "protocol": "TCP"}
            ]
            if "postgres" in name:
                ports = [{"name": "postgres", "port": 5432, "protocol": "TCP"}]
            elif "redis" in name:
                ports = [{"name": "redis", "port": 6379, "protocol": "TCP"}]

            services.append(
                InfrastructureService(
                    id=f"sim-svc-{name}",
                    name=name,
                    namespace="demomesh-sim",
                    service_type=svc_type,
                    cluster_ip=f"10.96.{len(services) + 1}.10",
                    ports=ports,
                    selectors={"app": name, "runtime": "demomesh"},
                    workload_count=1,
                    created_at="2026-11-01T00:00:00Z",
                )
            )
        return services

    @classmethod
    def list_workloads(cls, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        """Maps DemoMesh service instances to InfrastructureWorkload."""
        workloads = []
        latest_metrics = demo_mesh.get_latest_metrics()

        for name, meta in demo_mesh.SERVICE_DEFINITIONS.items():
            metrics = latest_metrics.get(name, {})
            err_rate = metrics.get("error_rate", 0.0)
            cpu = metrics.get("cpu_utilization", meta.get("base_cpu", 20.0))

            phase = WorkloadPhase.RUNNING
            restart_count = 0
            term_reason = None

            if name in demo_mesh.active_faults:
                fault = demo_mesh.active_faults[name]
                if fault.get("type") in ["crash", "oom"]:
                    phase = WorkloadPhase.CRASH_LOOP
                    restart_count = 3
                    term_reason = "OOMKilled" if fault.get("type") == "oom" else "Error"
                elif err_rate > 0.50:
                    phase = WorkloadPhase.FAILED
                else:
                    phase = WorkloadPhase.RUNNING

            workloads.append(
                InfrastructureWorkload(
                    id=f"sim-wl-{name}",
                    name=name,
                    namespace="demomesh-sim",
                    workload_type="SimulatedContainer",
                    desired_replicas=1,
                    ready_replicas=0 if phase in [WorkloadPhase.CRASH_LOOP, WorkloadPhase.FAILED] else 1,
                    restart_count=restart_count,
                    status=phase,
                    image=f"incidentx/sim-{name}:{meta.get('version', 'latest')}",
                    cpu_request_cores=0.25,
                    cpu_limit_cores=1.0,
                    memory_request_mb=128.0,
                    memory_limit_mb=512.0,
                    last_termination_reason=term_reason,
                    labels={"app": name, "tier": meta.get("tier", "Tier-1"), "runtime": "simulation"},
                )
            )
        return workloads

    @classmethod
    def get_workload_status(cls, workload_id: str) -> Optional[WorkloadStatus]:
        """Builds workload condition status for a simulated service container."""
        workloads = cls.list_workloads()
        target = next((w for w in workloads if w.id == workload_id or w.name == workload_id), None)
        if not target:
            return None

        ready = target.status == WorkloadPhase.RUNNING
        return WorkloadStatus(
            workload_id=target.id,
            name=target.name,
            namespace=target.namespace,
            phase=target.status,
            ready=ready,
            restart_count=target.restart_count,
            conditions=[
                {"type": "PodScheduled", "status": "True"},
                {"type": "Initialized", "status": "True"},
                {"type": "ContainersReady", "status": "True" if ready else "False"},
                {"type": "Ready", "status": "True" if ready else "False"},
            ],
            pod_statuses=[
                {
                    "pod_name": f"{target.name}-sim-0",
                    "phase": target.status.value,
                    "ready": ready,
                    "restart_count": target.restart_count,
                    "termination_reason": target.last_termination_reason,
                }
            ],
        )
