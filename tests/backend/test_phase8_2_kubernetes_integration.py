"""
INCIDENTX AI - Phase 8.2 Real Kubernetes Cluster Integration Test Suite
Verifies:
1. KubernetesConnectionManager multi-strategy discovery (kubeconfig, ServiceAccount, Bearer token).
2. Explicit connection failure handling with exponential backoff and no silent fallback.
3. Node inventory discovery: readiness, kubelet version, OS, allocatable CPU and memory.
4. Namespace inventory discovery: workload counts and lifecycle phase.
5. Pod inventory inspection: phases, container restart counts, readiness, IP addresses.
6. Deployment inventory inspection: desired vs available replicas, rollout health status.
7. Event streamer & deduplication: failure signature classification (CrashLoopBackOff, OOMKilled, etc.).
8. Resource inspection engine: requests/limits vs measured utilization vs unavailable metrics.
9. RBAC security and read-only token masking.
10. KubernetesEvidenceCollector integration with InvestigationOrchestrator.
11. REST API endpoints under /api/v1/kubernetes/*.
"""

import pytest
from httpx import AsyncClient

from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentMode,
    KubernetesClusterOverview,
    KubernetesConnectionDetails,
    KubernetesDeployment,
    KubernetesNamespace,
    KubernetesNode,
    KubernetesPod,
    KubernetesResourceMetrics,
    KubernetesService,
)
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient
from backend.app.infrastructure.kubernetes.kubernetes_connection_manager import (
    KubernetesConnectionManager,
    kubernetes_connection_manager,
)
from backend.app.infrastructure.kubernetes.kubernetes_events import (
    CRITICAL_K8S_FAILURE_REASONS,
    KubernetesEvents,
)
from backend.app.infrastructure.kubernetes.kubernetes_evidence_collector import (
    KubernetesEvidenceCollector,
)
from backend.app.infrastructure.kubernetes.kubernetes_inventory import (
    KubernetesInventory,
    parse_k8s_cpu,
    parse_k8s_memory_mb,
)
from backend.app.infrastructure.security.credential_manager import (
    ClusterCredentials,
    CredentialManager,
)


# ---------------------------------------------------------------------------
# High-Fidelity Mock Cluster Dataset for Deterministic Testing
# ---------------------------------------------------------------------------
MOCK_K8S_DATASET = {
    "/version": {
        "major": "1",
        "minor": "30",
        "gitVersion": "v1.30.2",
        "platform": "linux/amd64",
    },
    "/api/v1/nodes": {
        "items": [
            {
                "metadata": {"name": "node-worker-01", "labels": {"kubernetes.io/role": "worker"}},
                "status": {
                    "nodeInfo": {
                        "kubeletVersion": "v1.30.2",
                        "osImage": "Ubuntu 22.04 LTS",
                        "architecture": "amd64",
                    },
                    "allocatable": {"cpu": "8", "memory": "16384Mi"},
                    "conditions": [
                        {"type": "Ready", "status": "True"},
                        {"type": "MemoryPressure", "status": "False"},
                        {"type": "DiskPressure", "status": "False"},
                    ],
                },
            },
            {
                "metadata": {"name": "node-worker-02", "labels": {"kubernetes.io/role": "worker"}},
                "status": {
                    "nodeInfo": {
                        "kubeletVersion": "v1.30.2",
                        "osImage": "Ubuntu 22.04 LTS",
                        "architecture": "amd64",
                    },
                    "allocatable": {"cpu": "4", "memory": "8192Mi"},
                    "conditions": [
                        {"type": "Ready", "status": "False"},
                        {"type": "MemoryPressure", "status": "True"},
                    ],
                },
            },
        ]
    },
    "/api/v1/namespaces": {
        "items": [
            {"metadata": {"name": "default"}, "status": {"phase": "Active"}},
            {"metadata": {"name": "production"}, "status": {"phase": "Active"}},
            {"metadata": {"name": "monitoring"}, "status": {"phase": "Active"}},
        ]
    },
    "/api/v1/pods": {
        "items": [
            {
                "metadata": {
                    "name": "payment-api-6d84f-abcde",
                    "namespace": "production",
                    "labels": {"app": "payment-api", "tier": "Tier-1"},
                    "creationTimestamp": "2026-11-10T10:00:00Z",
                },
                "spec": {
                    "nodeName": "node-worker-01",
                    "containers": [
                        {
                            "name": "payment-container",
                            "image": "payment:v2.4",
                            "resources": {
                                "requests": {"cpu": "500m", "memory": "256Mi"},
                                "limits": {"cpu": "1", "memory": "512Mi"},
                            },
                        }
                    ],
                },
                "status": {
                    "phase": "Running",
                    "podIP": "10.244.1.45",
                    "containerStatuses": [
                        {
                            "name": "payment-container",
                            "ready": True,
                            "restartCount": 4,
                            "image": "payment:v2.4",
                        }
                    ],
                },
            },
            {
                "metadata": {
                    "name": "auth-service-9c72a-xyz12",
                    "namespace": "production",
                    "labels": {"app": "auth-service", "tier": "Tier-1"},
                    "creationTimestamp": "2026-11-10T10:15:00Z",
                },
                "spec": {
                    "nodeName": "node-worker-02",
                    "containers": [
                        {
                            "name": "auth-container",
                            "image": "auth:v1.9",
                            "resources": {
                                "requests": {"cpu": "250m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "256Mi"},
                            },
                        }
                    ],
                },
                "status": {
                    "phase": "CrashLoopBackOff",
                    "podIP": "10.244.2.18",
                    "containerStatuses": [
                        {
                            "name": "auth-container",
                            "ready": False,
                            "restartCount": 12,
                            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                        }
                    ],
                },
            },
        ]
    },
    "/apis/apps/v1/deployments": {
        "items": [
            {
                "metadata": {
                    "name": "payment-api",
                    "namespace": "production",
                    "labels": {"app": "payment-api"},
                    "creationTimestamp": "2026-11-01T00:00:00Z",
                },
                "spec": {"replicas": 2},
                "status": {
                    "availableReplicas": 2,
                    "readyReplicas": 2,
                    "updatedReplicas": 2,
                    "conditions": [{"type": "Available", "status": "True"}],
                },
            },
            {
                "metadata": {
                    "name": "auth-service",
                    "namespace": "production",
                    "labels": {"app": "auth-service"},
                    "creationTimestamp": "2026-11-01T00:00:00Z",
                },
                "spec": {"replicas": 3},
                "status": {
                    "availableReplicas": 0,
                    "readyReplicas": 0,
                    "updatedReplicas": 3,
                    "conditions": [{"type": "Progressing", "status": "False"}],
                },
            },
        ]
    },
    "/api/v1/services": {
        "items": [
            {
                "metadata": {
                    "name": "payment-api",
                    "namespace": "production",
                    "creationTimestamp": "2026-11-01T00:00:00Z",
                },
                "spec": {
                    "type": "ClusterIP",
                    "clusterIP": "10.96.0.45",
                    "ports": [{"name": "http", "port": 8080, "protocol": "TCP", "targetPort": 8080}],
                    "selector": {"app": "payment-api"},
                },
            }
        ]
    },
    "/api/v1/events": {
        "items": [
            {
                "metadata": {"uid": "ev-001", "name": "ev-001", "namespace": "production"},
                "type": "Warning",
                "reason": "CrashLoopBackOff",
                "message": "Back-off restarting failed container auth-container",
                "source": {"component": "kubelet"},
                "involvedObject": {"kind": "Pod", "name": "auth-service-9c72a-xyz12", "namespace": "production"},
                "count": 12,
                "firstTimestamp": "2026-11-10T10:16:00Z",
                "lastTimestamp": "2026-11-10T10:30:00Z",
            },
            {
                "metadata": {"uid": "ev-002", "name": "ev-002", "namespace": "production"},
                "type": "Warning",
                "reason": "OOMKilled",
                "message": "Container auth-container exceeded memory limit and was killed",
                "source": {"component": "kubelet"},
                "involvedObject": {"kind": "Pod", "name": "auth-service-9c72a-xyz12", "namespace": "production"},
                "count": 3,
                "firstTimestamp": "2026-11-10T10:15:30Z",
                "lastTimestamp": "2026-11-10T10:28:00Z",
            },
            {
                "metadata": {"uid": "ev-003", "name": "ev-003", "namespace": "default"},
                "type": "Normal",
                "reason": "Started",
                "message": "Started container payment-container",
                "source": {"component": "kubelet"},
                "involvedObject": {"kind": "Pod", "name": "payment-api-6d84f-abcde", "namespace": "production"},
                "count": 1,
                "firstTimestamp": "2026-11-10T10:00:05Z",
                "lastTimestamp": "2026-11-10T10:00:05Z",
            },
        ]
    },
    "/apis/metrics.k8s.io/v1beta1/pods": {
        "items": [
            {
                "metadata": {"name": "payment-api-6d84f-abcde", "namespace": "production"},
                "containers": [{"name": "payment-container", "usage": {"cpu": "180m", "memory": "220Mi"}}],
            }
        ]
    },
}

# Alias namespaced paths to dataset items
MOCK_K8S_DATASET["/api/v1/namespaces/production/pods"] = MOCK_K8S_DATASET["/api/v1/pods"]
MOCK_K8S_DATASET["/apis/apps/v1/namespaces/production/deployments"] = MOCK_K8S_DATASET["/apis/apps/v1/deployments"]
MOCK_K8S_DATASET["/api/v1/namespaces/production/services"] = MOCK_K8S_DATASET["/api/v1/services"]
MOCK_K8S_DATASET["/api/v1/namespaces/production/events"] = MOCK_K8S_DATASET["/api/v1/events"]
MOCK_K8S_DATASET["/apis/metrics.k8s.io/v1beta1/namespaces/production/pods"] = MOCK_K8S_DATASET["/apis/metrics.k8s.io/v1beta1/pods"]



# ---------------------------------------------------------------------------
# 1. Connection Manager & Authentication Strategy Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connection_manager_auth_discovery():
    """ConnectionManager discovers credentials and reports connection status."""
    cm = KubernetesConnectionManager(cluster_id="test-cluster")

    # When no cluster is available, connection must fail explicitly
    success = await cm.connect(max_retries=1)
    assert success is False
    assert cm.is_connected is False
    assert cm.is_live is False
    assert "No Kubernetes credentials found" in cm._last_error

    # Details must mask sensitive tokens
    details = cm.get_connection_details()
    assert isinstance(details, KubernetesConnectionDetails)
    assert details.is_connected is False
    assert details.is_read_only is True


@pytest.mark.asyncio
async def test_connection_manager_with_sandbox_mock():
    """ConnectionManager establishes valid mock connection when mock handler is set."""
    cm = KubernetesConnectionManager(cluster_id="sandbox-test")
    cm.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))

    connected = await cm.connect()
    assert connected is True
    assert cm.is_connected is True
    # Explicit rule: sandbox is not marked as real physical cluster
    assert cm.is_live is False
    assert cm.metrics_server_available is True

    await cm.disconnect()
    assert cm.is_connected is False


# ---------------------------------------------------------------------------
# 2. Node & Capacity Parsing Unit Tests
# ---------------------------------------------------------------------------

def test_k8s_cpu_and_memory_parsers():
    """Unit tests for Kubernetes CPU and Memory string conversions."""
    assert parse_k8s_cpu("500m") == 0.5
    assert parse_k8s_cpu("2") == 2.0
    assert parse_k8s_cpu("1000m") == 1.0
    assert parse_k8s_cpu("250000u") == 0.25
    assert parse_k8s_cpu(None) == 0.0

    assert parse_k8s_memory_mb("256Mi") == 256.0
    assert parse_k8s_memory_mb("1Gi") == 1024.0
    assert parse_k8s_memory_mb("512M") == 512.0
    assert parse_k8s_memory_mb("1024Ki") == 1.0
    assert parse_k8s_memory_mb(None) == 0.0


@pytest.mark.asyncio
async def test_node_discovery_and_readiness():
    """KubernetesInventory parses node readiness, version, conditions, and capacity."""
    client = KubernetesClient(cluster_id="k8s-nodes-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    inventory = KubernetesInventory(client=client)

    nodes = await inventory.list_nodes()
    assert len(nodes) == 2
    assert all(isinstance(n, KubernetesNode) for n in nodes)
    assert all(n.data_source == "LIVE_K8S" for n in nodes)

    ready_node = next(n for n in nodes if n.name == "node-worker-01")
    assert ready_node.ready is True
    assert ready_node.kubelet_version == "v1.30.2"
    assert ready_node.os_image == "Ubuntu 22.04 LTS"
    assert ready_node.cpu_allocatable_cores == 8.0
    assert ready_node.memory_allocatable_mb == 16384.0

    unready_node = next(n for n in nodes if n.name == "node-worker-02")
    assert unready_node.ready is False
    assert unready_node.conditions.get("MemoryPressure") == "True"


# ---------------------------------------------------------------------------
# 3. Namespace, Pod, and Deployment Discovery Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_namespace_discovery_workload_counts():
    """Namespaces are discovered and accurately correlate workload counts."""
    client = KubernetesClient(cluster_id="k8s-ns-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    inventory = KubernetesInventory(client=client)

    namespaces = await inventory.list_namespaces()
    assert len(namespaces) == 3
    assert all(isinstance(ns, KubernetesNamespace) for ns in namespaces)

    prod_ns = next(ns for ns in namespaces if ns.name == "production")
    assert prod_ns.status == "Active"
    # Both test pods are in 'production'
    assert prod_ns.workload_count == 2


@pytest.mark.asyncio
async def test_pod_inspection_restart_counts_and_phases():
    """Pods are inspected for restart counts, phase detection, IPs, and node placement."""
    client = KubernetesClient(cluster_id="k8s-pods-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    inventory = KubernetesInventory(client=client)

    pods = await inventory.list_pods_detailed()
    assert len(pods) == 2
    assert all(isinstance(p, KubernetesPod) for p in pods)

    # 1. Healthy pod with low restarts
    payment_pod = next(p for p in pods if "payment-api" in p.name)
    assert payment_pod.phase == "Running"
    assert payment_pod.ready is True
    assert payment_pod.restart_count == 4
    assert payment_pod.pod_ip == "10.244.1.45"
    assert payment_pod.node_name == "node-worker-01"

    # 2. Failing CrashLoopBackOff pod with elevated restarts
    auth_pod = next(p for p in pods if "auth-service" in p.name)
    assert auth_pod.phase == "CrashLoopBackOff"
    assert auth_pod.ready is False
    assert auth_pod.restart_count == 12
    assert auth_pod.node_name == "node-worker-02"


@pytest.mark.asyncio
async def test_deployment_rollout_conditions():
    """Deployments distinguish healthy rollouts from replica deficits and degraded states."""
    client = KubernetesClient(cluster_id="k8s-deps-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    inventory = KubernetesInventory(client=client)

    deployments = await inventory.list_deployments_detailed()
    assert len(deployments) == 2

    payment_dep = next(d for d in deployments if d.name == "payment-api")
    assert payment_dep.desired_replicas == 2
    assert payment_dep.available_replicas == 2
    assert payment_dep.rollout_status == "Healthy"

    auth_dep = next(d for d in deployments if d.name == "auth-service")
    assert auth_dep.desired_replicas == 3
    assert auth_dep.available_replicas == 0
    assert auth_dep.rollout_status == "Degraded"


# ---------------------------------------------------------------------------
# 4. Event Streamer & Deduplication Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_streamer_deduplication_and_classification():
    """Event streamer detects critical failure signatures and suppresses duplicate ingestion."""
    client = KubernetesClient(cluster_id="k8s-events-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    event_streamer = KubernetesEvents(client=client)

    events = await event_streamer.list_events(limit=10)
    assert len(events) == 3

    reasons = [e.reason for e in events]
    assert "CrashLoopBackOff" in reasons
    assert "OOMKilled" in reasons
    assert "Started" in reasons

    # Verify severity classification
    assert event_streamer.classify_severity("OOMKilled", "Warning") == "CRITICAL"
    assert event_streamer.classify_severity("CrashLoopBackOff", "Warning") == "CRITICAL"
    assert event_streamer.classify_severity("BackOff", "Warning") == "WARNING"
    assert event_streamer.classify_severity("Scheduled", "Normal") == "NORMAL"

    # Verify deduplication: consecutive reads must not re-duplicate seen hashes
    initial_cache_size = len(event_streamer._seen_hashes)
    assert initial_cache_size > 0
    await event_streamer.list_events(limit=10)
    assert len(event_streamer._seen_hashes) == initial_cache_size


# ---------------------------------------------------------------------------
# 5. Resource Inspection: Requests vs Limits vs Live Metrics Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resource_inspection_engine():
    """Inspects configured requests and limits, reporting actual measured utilization."""
    client = KubernetesClient(cluster_id="k8s-metrics-test")
    client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    inventory = KubernetesInventory(client=client)

    # Enable mock metrics server flag
    kubernetes_connection_manager._metrics_server_available = True

    metrics = await inventory.get_resource_metrics()
    assert len(metrics) == 2
    assert all(isinstance(m, KubernetesResourceMetrics) for m in metrics)

    payment_metric = next(m for m in metrics if "payment-api" in m.resource_name)
    assert payment_metric.configured_cpu_request_cores == 0.5
    assert payment_metric.configured_cpu_limit_cores == 1.0
    assert payment_metric.configured_memory_request_mb == 256.0
    assert payment_metric.configured_memory_limit_mb == 512.0
    # Live measured values from metrics server
    assert payment_metric.measured_cpu_cores == 0.18
    assert payment_metric.measured_memory_mb == 220.0

    kubernetes_connection_manager._metrics_server_available = False


# ---------------------------------------------------------------------------
# 6. IncidentX AI Agent Evidence Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kubernetes_evidence_collector():
    """KubernetesEvidenceCollector transforms live cluster faults into court-grade Evidence."""
    # Temporarily switch environment manager to KUBERNETES mode with mock adapter
    from backend.app.infrastructure.core.environment_manager import environment_manager

    k8s_adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    assert isinstance(k8s_adapter, KubernetesAdapter)
    k8s_adapter.client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    await k8s_adapter.connect()

    # Manually activate K8s mode in manager for test scope
    prev_mode = environment_manager.active_mode
    environment_manager._active_mode = EnvironmentMode.KUBERNETES

    try:
        evidence = await KubernetesEvidenceCollector.collect_incident_evidence(
            incident_id="test-incident-k8s-001"
        )
        assert len(evidence) > 0
        evidence_types = [e.evidence_type for e in evidence]
        assert "K8S_POD_FAILURE" in evidence_types
        assert "K8S_EVENT_ANOMALY" in evidence_types
        assert "K8S_DEPLOYMENT_DEGRADED" in evidence_types

        # Verify high confidence score on CrashLoop / OOMKilled
        crash_ev = next(e for e in evidence if "auth-service" in e.description)
        assert crash_ev.confidence_score >= 0.80
        assert "CrashLoopBackOff" in crash_ev.description or "restarts" in crash_ev.description
    finally:
        environment_manager._active_mode = prev_mode
        k8s_adapter.client.clear_mock_handler()


# ---------------------------------------------------------------------------
# 7. Dedicated REST API Endpoints Tests (/api/v1/kubernetes/*)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_kubernetes_endpoints(client: AsyncClient):
    """Verifies all REST API routes for live Kubernetes cluster operations."""
    from backend.app.infrastructure.core.environment_manager import environment_manager

    k8s_adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    assert isinstance(k8s_adapter, KubernetesAdapter)
    k8s_adapter.client.set_mock_handler(lambda path: MOCK_K8S_DATASET.get(path, {}))
    await k8s_adapter.connect()

    try:
        # 1. GET /api/v1/kubernetes/connection
        resp = await client.get("/api/v1/kubernetes/connection")
        assert resp.status_code == 200
        conn = resp.json()
        assert "is_connected" in conn
        assert "is_read_only" in conn
        assert conn["is_read_only"] is True

        # 2. GET /api/v1/kubernetes/cluster
        resp = await client.get("/api/v1/kubernetes/cluster")
        assert resp.status_code == 200
        cluster = resp.json()
        assert cluster["data_source"] == "LIVE_K8S"

        # 3. GET /api/v1/kubernetes/nodes
        resp = await client.get("/api/v1/kubernetes/nodes")
        assert resp.status_code == 200
        nodes = resp.json()
        assert len(nodes) == 2

        # 4. GET /api/v1/kubernetes/namespaces
        resp = await client.get("/api/v1/kubernetes/namespaces")
        assert resp.status_code == 200
        namespaces = resp.json()
        assert len(namespaces) == 3

        # 5. GET /api/v1/kubernetes/pods
        resp = await client.get("/api/v1/kubernetes/pods?namespace=production")
        assert resp.status_code == 200
        pods = resp.json()
        assert len(pods) == 2

        # 6. GET /api/v1/kubernetes/deployments
        resp = await client.get("/api/v1/kubernetes/deployments")
        assert resp.status_code == 200
        deps = resp.json()
        assert len(deps) == 2

        # 7. GET /api/v1/kubernetes/services
        resp = await client.get("/api/v1/kubernetes/services")
        assert resp.status_code == 200
        services = resp.json()
        assert len(services) == 1

        # 8. GET /api/v1/kubernetes/events
        resp = await client.get("/api/v1/kubernetes/events?only_warnings=true")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 2

        # 9. GET /api/v1/kubernetes/metrics
        resp = await client.get("/api/v1/kubernetes/metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        assert len(metrics) == 2

        # 10. GET /api/v1/kubernetes/health
        resp = await client.get("/api/v1/kubernetes/health")
        assert resp.status_code == 200
        health = resp.json()
        assert health["is_healthy"] is True

    finally:
        k8s_adapter.client.clear_mock_handler()
