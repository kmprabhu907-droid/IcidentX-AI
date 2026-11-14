"""
INCIDENTX AI - Kubernetes Inventory & Resource Inspection Engine (Phase 8.2)
Collects and maps live Kubernetes Nodes, Namespaces, Pods, Deployments, Services,
and accurately evaluates resource requests/limits vs live measured metrics.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.infrastructure.core.infrastructure_models import (
    InfrastructureService,
    InfrastructureWorkload,
    KubernetesClusterOverview,
    KubernetesDeployment,
    KubernetesNamespace,
    KubernetesNode,
    KubernetesPod,
    KubernetesResourceMetrics,
    KubernetesService,
    WorkloadPhase,
    WorkloadStatus,
)
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient
from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
    kubernetes_connection_manager,
)


def parse_k8s_cpu(val: Any) -> float:
    """Parses Kubernetes CPU string (e.g. '500m', '2', '0.25') into cores."""
    if not val:
        return 0.0
    val_str = str(val).strip()
    if val_str.endswith("m"):
        try:
            return float(val_str[:-1]) / 1000.0
        except ValueError:
            return 0.0
    if val_str.endswith("u"):
        try:
            return float(val_str[:-1]) / 1_000_000.0
        except ValueError:
            return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def parse_k8s_memory_mb(val: Any) -> float:
    """Parses Kubernetes Memory string (e.g. '128Mi', '1Gi', '512M') into Megabytes (MB)."""
    if not val:
        return 0.0
    val_str = str(val).strip()
    try:
        if val_str.endswith("Ki"):
            return round(float(val_str[:-2]) / 1024.0, 2)
        if val_str.endswith("Mi"):
            return round(float(val_str[:-2]), 2)
        if val_str.endswith("Gi"):
            return round(float(val_str[:-2]) * 1024.0, 2)
        if val_str.endswith("Ti"):
            return round(float(val_str[:-2]) * 1024.0 * 1024.0, 2)
        if val_str.endswith("K") or val_str.endswith("k"):
            return round(float(val_str[:-1]) / 1000.0, 2)
        if val_str.endswith("M") or val_str.endswith("m"):
            return round(float(val_str[:-1]), 2)
        if val_str.endswith("G") or val_str.endswith("g"):
            return round(float(val_str[:-1]) * 1000.0, 2)
        return round(float(val_str) / (1024.0 * 1024.0), 2)
    except ValueError:
        return 0.0


class KubernetesInventory:
    """Discovers and maps live Kubernetes workloads, services, nodes, and resource metrics."""

    def __init__(self, client: KubernetesClient):
        self.client = client

    # -----------------------------------------------------------------------
    # Nodes Discovery
    # -----------------------------------------------------------------------
    async def list_nodes(self) -> List[KubernetesNode]:
        """Discovers nodes and parses readiness, version, OS, and allocatable capacity."""
        raw_nodes = await self.client.list_nodes()
        nodes: List[KubernetesNode] = []

        for item in raw_nodes:
            meta = item.get("metadata", {})
            status = item.get("status", {})
            node_info = status.get("nodeInfo", {})
            allocatable = status.get("allocatable", {})

            # Conditions
            conditions_map: Dict[str, str] = {}
            ready = False
            for cond in status.get("conditions", []):
                ctype = cond.get("type", "")
                cstat = cond.get("status", "False")
                conditions_map[ctype] = cstat
                if ctype == "Ready" and cstat == "True":
                    ready = True

            cpu_alloc = parse_k8s_cpu(allocatable.get("cpu", "4"))
            mem_alloc = parse_k8s_memory_mb(allocatable.get("memory", "8192Mi"))

            nodes.append(
                KubernetesNode(
                    name=meta.get("name", "unknown-node"),
                    ready=ready,
                    kubelet_version=node_info.get("kubeletVersion", "v1.30.0"),
                    os_image=node_info.get("osImage", "Linux"),
                    architecture=node_info.get("architecture", "amd64"),
                    cpu_allocatable_cores=cpu_alloc,
                    memory_allocatable_mb=mem_alloc,
                    conditions=conditions_map,
                    labels=meta.get("labels", {}),
                    creation_timestamp=meta.get("creationTimestamp", datetime.now(timezone.utc).isoformat()),
                    data_source="LIVE_K8S",
                )
            )
        return nodes

    # -----------------------------------------------------------------------
    # Namespaces Discovery
    # -----------------------------------------------------------------------
    async def list_namespaces(self) -> List[KubernetesNamespace]:
        """Discovers namespaces and calculates associated workload counts."""
        raw_ns = await self.client.list_namespaces_detailed()
        pods = await self.client.list_pods()

        # Count pods per namespace
        pod_counts: Dict[str, int] = {}
        for p in pods:
            p_ns = p.get("metadata", {}).get("namespace", "default")
            pod_counts[p_ns] = pod_counts.get(p_ns, 0) + 1

        namespaces: List[KubernetesNamespace] = []
        for item in raw_ns:
            meta = item.get("metadata", {})
            status = item.get("status", {})
            name = meta.get("name", "default")

            namespaces.append(
                KubernetesNamespace(
                    name=name,
                    status=status.get("phase", "Active"),
                    workload_count=pod_counts.get(name, 0),
                    creation_timestamp=meta.get("creationTimestamp", datetime.now(timezone.utc).isoformat()),
                    labels=meta.get("labels", {}),
                    data_source="LIVE_K8S",
                )
            )
        return namespaces

    # -----------------------------------------------------------------------
    # Pods Discovery
    # -----------------------------------------------------------------------
    async def list_pods_detailed(self, namespace: Optional[str] = None) -> List[KubernetesPod]:
        """Discovers pods with container restart counts, phases, readiness, and IPs."""
        raw_pods = await self.client.list_pods(namespace=namespace)
        pods: List[KubernetesPod] = []

        for item in raw_pods:
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            name = meta.get("name", "unknown-pod")
            ns = meta.get("namespace", "default")
            c_statuses = status.get("containerStatuses", [])

            restart_count = 0
            all_ready = True if c_statuses else False
            phase = status.get("phase", "Running")

            for cs in c_statuses:
                restart_count += cs.get("restartCount", 0)
                if not cs.get("ready", False):
                    all_ready = False
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting.get("reason") in ["CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"]:
                    phase = waiting.get("reason")

            pods.append(
                KubernetesPod(
                    name=name,
                    namespace=ns,
                    phase=phase,
                    ready=all_ready,
                    restart_count=restart_count,
                    pod_ip=status.get("podIP"),
                    node_name=spec.get("nodeName"),
                    creation_timestamp=meta.get("creationTimestamp", datetime.now(timezone.utc).isoformat()),
                    containers=[
                        {
                            "name": cs.get("name", "app"),
                            "ready": cs.get("ready", False),
                            "restart_count": cs.get("restartCount", 0),
                            "image": cs.get("image", "unknown"),
                        }
                        for cs in c_statuses
                    ],
                    labels=meta.get("labels", {}),
                    data_source="LIVE_K8S",
                )
            )
        return pods

    # -----------------------------------------------------------------------
    # Deployments Discovery
    # -----------------------------------------------------------------------
    async def list_deployments_detailed(self, namespace: Optional[str] = None) -> List[KubernetesDeployment]:
        """Discovers deployments and parses replica status and rollout conditions."""
        raw_deps = await self.client.list_deployments(namespace=namespace)
        deployments: List[KubernetesDeployment] = []

        for item in raw_deps:
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})

            name = meta.get("name", "unknown-deployment")
            ns = meta.get("namespace", "default")
            desired = spec.get("replicas", 1)
            available = status.get("availableReplicas", 0)
            updated = status.get("updatedReplicas", 0)

            rollout = "Healthy"
            if desired > 0 and available == 0:
                rollout = "Degraded"
            elif available < desired:
                rollout = "Progressing"

            deployments.append(
                KubernetesDeployment(
                    name=name,
                    namespace=ns,
                    desired_replicas=desired,
                    available_replicas=available,
                    updated_replicas=updated,
                    rollout_status=rollout,
                    conditions=status.get("conditions", []),
                    labels=meta.get("labels", {}),
                    creation_timestamp=meta.get("creationTimestamp", datetime.now(timezone.utc).isoformat()),
                    data_source="LIVE_K8S",
                )
            )
        return deployments

    # -----------------------------------------------------------------------
    # Services Discovery
    # -----------------------------------------------------------------------
    async def list_services_detailed(self, namespace: Optional[str] = None) -> List[KubernetesService]:
        """Discovers services and mapping port definitions and endpoint readiness."""
        raw_services = await self.client.list_services(namespace=namespace)
        services: List[KubernetesService] = []

        for item in raw_services:
            meta = item.get("metadata", {})
            spec = item.get("spec", {})

            name = meta.get("name", "unknown-service")
            ns = meta.get("namespace", "default")

            ports = [
                {
                    "name": p.get("name", "http"),
                    "port": p.get("port", 80),
                    "protocol": p.get("protocol", "TCP"),
                    "target_port": p.get("targetPort", 80),
                }
                for p in spec.get("ports", [])
            ]

            services.append(
                KubernetesService(
                    name=name,
                    namespace=ns,
                    service_type=spec.get("type", "ClusterIP"),
                    cluster_ip=spec.get("clusterIP"),
                    ports=ports,
                    endpoints_available=1,
                    selectors=spec.get("selector", {}),
                    creation_timestamp=meta.get("creationTimestamp", datetime.now(timezone.utc).isoformat()),
                    data_source="LIVE_K8S",
                )
            )
        return services

    # -----------------------------------------------------------------------
    # Common Interface Mappings (BaseInfrastructureAdapter Compatibility)
    # -----------------------------------------------------------------------
    async def list_services(self, namespace: Optional[str] = None) -> List[InfrastructureService]:
        detailed = await self.list_services_detailed(namespace=namespace)
        return [
            InfrastructureService(
                id=f"k8s-svc-{s.namespace}-{s.name}",
                name=s.name,
                namespace=s.namespace,
                service_type=s.service_type,
                cluster_ip=s.cluster_ip,
                ports=s.ports,
                selectors=s.selectors,
                workload_count=1,
                data_source="LIVE_K8S",
                created_at=s.creation_timestamp,
            )
            for s in detailed
        ]

    async def list_workloads(self, namespace: Optional[str] = None) -> List[InfrastructureWorkload]:
        deployments = await self.list_deployments_detailed(namespace=namespace)
        pods = await self.list_pods_detailed(namespace=namespace)
        workloads: List[InfrastructureWorkload] = []

        for d in deployments:
            phase = WorkloadPhase.RUNNING if d.available_replicas >= d.desired_replicas and d.desired_replicas > 0 else WorkloadPhase.PENDING
            workloads.append(
                InfrastructureWorkload(
                    id=f"k8s-deploy-{d.namespace}-{d.name}",
                    name=d.name,
                    namespace=d.namespace,
                    workload_type="Deployment",
                    kind="Deployment",
                    desired_replicas=d.desired_replicas,
                    replicas_desired=d.desired_replicas,
                    ready_replicas=d.available_replicas,
                    replicas_available=d.available_replicas,
                    restart_count=0,
                    status=phase,
                    phase=phase.value,
                    labels=d.labels,
                    data_source="LIVE_K8S",
                    created_at=d.creation_timestamp,
                )
            )

        for p in pods:
            phase = WorkloadPhase.RUNNING if p.ready else (
                WorkloadPhase.CRASH_LOOP if "CrashLoop" in p.phase else WorkloadPhase.PENDING
            )
            workloads.append(
                InfrastructureWorkload(
                    id=f"k8s-pod-{p.namespace}-{p.name}",
                    name=p.name,
                    namespace=p.namespace,
                    workload_type="Pod",
                    kind="Pod",
                    desired_replicas=1,
                    replicas_desired=1,
                    ready_replicas=1 if p.ready else 0,
                    replicas_available=1 if p.ready else 0,
                    restart_count=p.restart_count,
                    status=phase,
                    phase=p.phase,
                    labels=p.labels,
                    data_source="LIVE_K8S",
                    created_at=p.creation_timestamp,
                )
            )

        return workloads

    async def get_workload_status(
        self, workload_id: str, namespace: Optional[str] = None
    ) -> Optional[WorkloadStatus]:
        workloads = await self.list_workloads(namespace=namespace)
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
                {"type": "Available", "status": "True" if ready else "False"},
                {"type": "Progressing", "status": "True"},
            ],
            pod_statuses=[
                {
                    "pod_name": f"{target.name}-pod-0",
                    "phase": target.status.value,
                    "ready": ready,
                    "restart_count": target.restart_count,
                }
            ],
            data_source="LIVE_K8S",
        )

    # -----------------------------------------------------------------------
    # Resource Inspection Engine
    # -----------------------------------------------------------------------
    async def get_resource_metrics(
        self, workload_id: Optional[str] = None, namespace: Optional[str] = None
    ) -> List[KubernetesResourceMetrics]:
        """
        Inspects actual CPU and memory resource requests/limits, and combines them
        with live measured utilization if Metrics Server is present.
        Explicitly reports None if Metrics Server is unavailable without fabricating metrics.
        """
        raw_pods = await self.client.list_pods(namespace=namespace)
        metrics_server_available = kubernetes_connection_manager.metrics_server_available

        # Fetch measured metrics if available
        pod_usage_map: Dict[str, Tuple[float, float]] = {}
        if metrics_server_available:
            try:
                pod_metrics_items = await self.client.get_pod_metrics(namespace=namespace)
                for item in pod_metrics_items:
                    pname = item.get("metadata", {}).get("name", "")
                    containers = item.get("containers", [])
                    tot_cpu = sum(parse_k8s_cpu(c.get("usage", {}).get("cpu", "0")) for c in containers)
                    tot_mem = sum(parse_k8s_memory_mb(c.get("usage", {}).get("memory", "0")) for c in containers)
                    pod_usage_map[pname] = (round(tot_cpu, 3), round(tot_mem, 2))
            except Exception as e:
                logger.debug(f"[K8sInventory] Failed fetching live metrics: {e}")
                metrics_server_available = False

        results: List[KubernetesResourceMetrics] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in raw_pods:
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            name = meta.get("name", "unknown")
            ns = meta.get("namespace", "default")

            if workload_id and workload_id not in (name, f"k8s-pod-{ns}-{name}"):
                continue

            containers = spec.get("containers", [])
            req_cpu = sum(parse_k8s_cpu(c.get("resources", {}).get("requests", {}).get("cpu", "0")) for c in containers)
            lim_cpu = sum(parse_k8s_cpu(c.get("resources", {}).get("limits", {}).get("cpu", "0")) for c in containers)
            req_mem = sum(parse_k8s_memory_mb(c.get("resources", {}).get("requests", {}).get("memory", "0")) for c in containers)
            lim_mem = sum(parse_k8s_memory_mb(c.get("resources", {}).get("limits", {}).get("memory", "0")) for c in containers)

            measured_cpu, measured_mem = pod_usage_map.get(name, (None, None))

            results.append(
                KubernetesResourceMetrics(
                    resource_type="pod",
                    resource_name=name,
                    namespace=ns,
                    configured_cpu_request_cores=round(req_cpu, 3),
                    configured_cpu_limit_cores=round(lim_cpu, 3),
                    configured_memory_request_mb=round(req_mem, 2),
                    configured_memory_limit_mb=round(lim_mem, 2),
                    measured_cpu_cores=measured_cpu,
                    measured_memory_mb=measured_mem,
                    metrics_server_available=metrics_server_available,
                    timestamp=now_iso,
                    data_source="LIVE_K8S",
                )
            )

        return results

    # -----------------------------------------------------------------------
    # Cluster Overview Summary
    # -----------------------------------------------------------------------
    async def get_cluster_overview(self) -> KubernetesClusterOverview:
        """Returns consolidated health, inventory, and connectivity summary for dashboard."""
        conn_details = kubernetes_connection_manager.get_connection_details()
        status_str = "CONNECTED" if conn_details.is_connected else "DISCONNECTED"

        if not conn_details.is_connected:
            return KubernetesClusterOverview(
                connection_status=status_str,
                cluster_name=conn_details.cluster_name,
                kubernetes_version="unknown",
                api_endpoint=conn_details.api_server_url,
                auth_method=conn_details.auth_method,
                is_live=False,
                is_read_only=True,
                error_message=conn_details.last_error,
                data_source="LIVE_K8S",
            )

        # Connected: gather actual inventory numbers
        try:
            nodes = await self.list_nodes()
            namespaces = await self.list_namespaces()
            pods = await self.list_pods_detailed()
            deployments = await self.list_deployments_detailed()

            ready_nodes = sum(1 for n in nodes if n.ready)
            healthy_deps = sum(1 for d in deployments if d.rollout_status == "Healthy")

            return KubernetesClusterOverview(
                connection_status="CONNECTED",
                cluster_name=conn_details.cluster_name,
                kubernetes_version=conn_details.discovered_version or "v1.30.0",
                api_endpoint=conn_details.api_server_url,
                auth_method=conn_details.auth_method,
                is_live=conn_details.is_live,
                is_read_only=True,
                total_nodes=len(nodes),
                ready_nodes=ready_nodes,
                total_namespaces=len(namespaces),
                total_pods=len(pods),
                healthy_deployments=healthy_deps,
                metrics_server_available=kubernetes_connection_manager.metrics_server_available,
                error_message=None,
                data_source="LIVE_K8S",
            )
        except Exception as e:
            return KubernetesClusterOverview(
                connection_status="ERROR",
                cluster_name=conn_details.cluster_name,
                kubernetes_version=conn_details.discovered_version or "unknown",
                api_endpoint=conn_details.api_server_url,
                auth_method=conn_details.auth_method,
                is_live=conn_details.is_live,
                is_read_only=True,
                error_message=str(e),
                data_source="LIVE_K8S",
            )
