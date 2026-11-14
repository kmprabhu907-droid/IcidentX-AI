"""
INCIDENTX AI - Phase 8.1 Dual-Environment Abstraction Engine Test Suite
Verifies:
1. DemoMeshAdapter implements BaseInfrastructureAdapter common interface.
2. KubernetesAdapter implements BaseInfrastructureAdapter common interface (read-only).
3. DemoMesh inventory, metrics, health, and events return valid data tagged SIMULATED.
4. KubernetesAdapter with mock API client handles discovery, pods, restarts, events (tagged LIVE_K8S).
5. EnvironmentManager switching between DemoMesh and Kubernetes.
6. EnvironmentManager explicit failure (no silent fallback from Kubernetes to DemoMesh).
7. EnvironmentAccessPolicy RBAC verification (Super Admin, Organization Admin, SRE Lead).
8. Cross-environment data isolation and ContextVar tagging.
9. CredentialManager token masking and separation of read-only vs remediation credentials.
10. FastAPI API endpoints under /api/v1/environments.
"""

import pytest
from httpx import AsyncClient

from backend.app.infrastructure.core.base_adapter import BaseInfrastructureAdapter
from backend.app.infrastructure.core.environment_context import (
    EnvironmentContext,
    get_current_data_source,
    get_current_environment_mode,
)
from backend.app.infrastructure.core.environment_manager import (
    EnvironmentConnectionException,
    EnvironmentManager,
    environment_manager,
)
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentHealth,
    EnvironmentMetadata,
    EnvironmentMode,
    InfrastructureEvent,
    InfrastructureService,
    InfrastructureWorkload,
    ResourceMetric,
)
from backend.app.infrastructure.demomesh.demomesh_adapter import DemoMeshAdapter
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient
from backend.app.infrastructure.security.credential_manager import (
    CredentialManager,
    KubernetesCredentials,
)
from backend.app.infrastructure.security.environment_access_policy import (
    EnvironmentAccessPolicy,
)
from backend.app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# 1. Interface Conformance Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_demomesh_adapter_implements_common_interface():
    """DemoMeshAdapter must subclass BaseInfrastructureAdapter and fulfill interface contracts."""
    adapter = DemoMeshAdapter()
    assert isinstance(adapter, BaseInfrastructureAdapter)
    assert adapter.mode == EnvironmentMode.DEMOMESH
    assert adapter.is_read_only is False
    assert adapter.data_source == "SIMULATED"

    connected = await adapter.connect()
    assert connected is True

    meta = await adapter.get_environment_metadata()
    assert isinstance(meta, EnvironmentMetadata)
    assert meta.mode == EnvironmentMode.DEMOMESH
    assert meta.is_simulated is True
    assert meta.data_source == "SIMULATED"

    health = await adapter.health_check()
    assert isinstance(health, EnvironmentHealth)
    assert health.mode == EnvironmentMode.DEMOMESH
    assert health.data_source == "SIMULATED"
    assert health.is_healthy is True

    await adapter.disconnect()


@pytest.mark.asyncio
async def test_kubernetes_adapter_implements_common_interface():
    """KubernetesAdapter must subclass BaseInfrastructureAdapter and enforce read-only status in 8.1."""
    adapter = KubernetesAdapter()
    assert isinstance(adapter, BaseInfrastructureAdapter)
    assert adapter.mode == EnvironmentMode.KUBERNETES
    assert adapter.is_read_only is True
    assert adapter.data_source == "LIVE_K8S"

    meta = await adapter.get_environment_metadata()
    assert isinstance(meta, EnvironmentMetadata)
    assert meta.mode == EnvironmentMode.KUBERNETES
    assert meta.is_simulated is False
    assert meta.data_source == "LIVE_K8S"
    assert meta.is_read_only is True


# ---------------------------------------------------------------------------
# 2. DemoMesh Adapter Telemetry & Inventory Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_demomesh_inventory_and_metrics():
    """DemoMeshAdapter must return services, workloads, metrics, and events tagged SIMULATED."""
    adapter = DemoMeshAdapter()
    await adapter.connect()

    services = await adapter.list_services()
    assert len(services) > 0
    assert all(isinstance(s, InfrastructureService) for s in services)
    assert all(s.data_source == "SIMULATED" for s in services)

    service_names = [s.name for s in services]
    assert "api-gateway" in service_names

    workloads = await adapter.list_workloads()
    assert len(workloads) > 0
    assert all(isinstance(w, InfrastructureWorkload) for w in workloads)
    assert all(w.data_source == "SIMULATED" for w in workloads)

    # Workload status check
    w_status = await adapter.get_workload_status(workload_id="api-gateway")
    assert w_status is not None
    assert w_status.name == "api-gateway"
    assert w_status.data_source == "SIMULATED"

    # Events check
    events = await adapter.get_events(limit=10)
    assert isinstance(events, list)
    assert all(isinstance(e, InfrastructureEvent) for e in events)
    assert all(e.data_source == "SIMULATED" for e in events)

    # Metrics check
    metrics = await adapter.get_resource_metrics(workload_id="api-gateway")
    assert isinstance(metrics, list)
    assert len(metrics) > 0
    assert all(isinstance(m, ResourceMetric) for m in metrics)
    assert all(m.data_source == "SIMULATED" for m in metrics)

    await adapter.disconnect()


# ---------------------------------------------------------------------------
# 3. Kubernetes Adapter with Mock Handler Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_kubernetes_adapter_with_mock_client():
    """KubernetesAdapter queries Kubernetes API, returning real K8s resources tagged LIVE_K8S."""
    mock_responses = {
        "/version": {
            "major": "1",
            "minor": "30",
            "gitVersion": "v1.30.2",
            "platform": "linux/amd64",
        },
        "/api/v1/namespaces": {
            "items": [
                {"metadata": {"name": "default"}},
                {"metadata": {"name": "production"}},
            ]
        },
        "/api/v1/namespaces/production/pods": {
            "items": [
                {
                    "metadata": {
                        "name": "checkout-service-7f49b-abcde",
                        "namespace": "production",
                        "labels": {"app": "checkout-service"},
                        "creationTimestamp": "2026-11-10T12:00:00Z",
                    },
                    "status": {
                        "phase": "Running",
                        "containerStatuses": [
                            {"restartCount": 3, "ready": True, "name": "checkout"}
                        ],
                    },
                }
            ]
        },
        "/apis/apps/v1/namespaces/production/deployments": {
            "items": [
                {
                    "metadata": {
                        "name": "checkout-service",
                        "namespace": "production",
                        "labels": {"app": "checkout-service"},
                    },
                    "spec": {"replicas": 3},
                    "status": {"readyReplicas": 3, "availableReplicas": 3},
                }
            ]
        },
        "/api/v1/namespaces/production/services": {
            "items": [
                {
                    "metadata": {
                        "name": "checkout-service",
                        "namespace": "production",
                        "labels": {"tier": "Tier-1"},
                    },
                    "spec": {
                        "clusterIP": "10.96.12.34",
                        "ports": [{"port": 8080, "protocol": "TCP"}],
                    },
                }
            ]
        },
        "/api/v1/namespaces/production/events": {
            "items": [
                {
                    "metadata": {
                        "name": "checkout-ev-1",
                        "namespace": "production",
                        "creationTimestamp": "2026-11-10T12:05:00Z",
                    },
                    "type": "Warning",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container checkout",
                    "source": {"component": "kubelet"},
                    "involvedObject": {"kind": "Pod", "name": "checkout-service-7f49b-abcde"},
                }
            ]
        },
    }

    client = KubernetesClient(namespace="production")
    client.set_mock_handler(lambda path: mock_responses.get(path, {}))

    adapter = KubernetesAdapter(client=client)
    connected = await adapter.connect()
    assert connected is True

    meta = await adapter.get_environment_metadata()
    assert meta.mode == EnvironmentMode.KUBERNETES
    assert meta.cluster_version == "v1.30.2"
    assert meta.data_source == "LIVE_K8S"

    health = await adapter.health_check()
    assert health.is_healthy is True
    assert health.data_source == "LIVE_K8S"

    # Services
    services = await adapter.list_services()
    assert len(services) == 1
    assert services[0].name == "checkout-service"
    assert services[0].data_source == "LIVE_K8S"

    # Workloads
    workloads = await adapter.list_workloads()
    assert len(workloads) == 2  # 1 deployment + 1 pod
    pod_workload = next(w for w in workloads if w.kind == "Pod")
    assert pod_workload.restart_count == 3
    assert pod_workload.phase == "Running"
    assert pod_workload.data_source == "LIVE_K8S"

    # Events
    events = await adapter.get_events()
    assert len(events) == 1
    assert events[0].reason == "BackOff"
    assert events[0].event_type == "Warning"
    assert events[0].data_source == "LIVE_K8S"

    await adapter.disconnect()
    client.clear_mock_handler()


# ---------------------------------------------------------------------------
# 4. Environment Switching & Non-Fallback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_environment_manager_switching():
    """EnvironmentManager switches between DemoMesh and Kubernetes cleanly."""
    manager = EnvironmentManager()
    await manager.initialize()
    assert manager.active_mode == EnvironmentMode.DEMOMESH

    # Mock K8s client so it connects successfully
    k8s_adapter = manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    assert isinstance(k8s_adapter, KubernetesAdapter)
    k8s_adapter.client.set_mock_handler(
        lambda p: {"gitVersion": "v1.30.0", "items": []}
    )

    admin_user = User(
        id="usr-admin",
        email="admin@incidentx.internal",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )

    meta_k8s = await manager.switch_environment(
        target_mode=EnvironmentMode.KUBERNETES, user=admin_user
    )
    assert manager.active_mode == EnvironmentMode.KUBERNETES
    assert meta_k8s.mode == EnvironmentMode.KUBERNETES
    assert meta_k8s.data_source == "LIVE_K8S"

    # Switch back to DEMOMESH
    meta_mesh = await manager.switch_environment(
        target_mode=EnvironmentMode.DEMOMESH, user=admin_user
    )
    assert manager.active_mode == EnvironmentMode.DEMOMESH
    assert meta_mesh.mode == EnvironmentMode.DEMOMESH
    assert meta_mesh.data_source == "SIMULATED"

    k8s_adapter.client.clear_mock_handler()


@pytest.mark.asyncio
async def test_environment_manager_fails_explicitly_without_silent_fallback():
    """
    CRITICAL SAFETY REQUIREMENT:
    When Kubernetes fails to connect, EnvironmentManager must raise an explicit
    exception and MUST NOT silently fall back to DemoMesh simulation.
    """
    manager = EnvironmentManager()
    await manager.initialize()
    assert manager.active_mode == EnvironmentMode.DEMOMESH

    # Configure K8s adapter client to simulate unreachable endpoint
    k8s_adapter = manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    assert isinstance(k8s_adapter, KubernetesAdapter)

    def failing_handler(path):
        raise ConnectionRefusedError("Failed to reach Kubernetes API server at 127.0.0.1:6443")

    k8s_adapter.client.set_mock_handler(failing_handler)

    admin_user = User(
        id="usr-admin",
        email="admin@incidentx.internal",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )

    # Attempting to switch must raise EnvironmentConnectionException
    with pytest.raises(EnvironmentConnectionException) as exc_info:
        await manager.switch_environment(
            target_mode=EnvironmentMode.KUBERNETES, user=admin_user
        )

    assert "Failed to connect to 'KUBERNETES'" in str(exc_info.value)

    # Active mode MUST remain DEMOMESH and not masquerade as Kubernetes
    assert manager.active_mode == EnvironmentMode.DEMOMESH
    assert manager.active_adapter.mode == EnvironmentMode.DEMOMESH
    assert manager.active_adapter.data_source == "SIMULATED"

    k8s_adapter.client.clear_mock_handler()


# ---------------------------------------------------------------------------
# 5. Security & Access Policy (RBAC) Tests
# ---------------------------------------------------------------------------

def test_environment_access_policy_rbac():
    """Only SUPER_ADMIN, ORGANIZATION_ADMIN, and SRE_LEAD may switch infrastructure environments."""
    super_admin = User(id="1", email="super@x.io", role=UserRole.SUPER_ADMIN, is_active=True)
    org_admin = User(id="2", email="admin@x.io", role=UserRole.ORGANIZATION_ADMIN, is_active=True)
    sre_eng = User(id="3", email="eng@x.io", role=UserRole.SRE_ENGINEER, is_active=True)
    viewer = User(id="4", email="viewer@x.io", role=UserRole.READ_ONLY_VIEWER, is_active=True)

    assert EnvironmentAccessPolicy.can_switch_environment(super_admin, strict=True) is True
    assert EnvironmentAccessPolicy.can_switch_environment(org_admin, strict=True) is True

    assert EnvironmentAccessPolicy.can_switch_environment(sre_eng, strict=True) is False
    assert EnvironmentAccessPolicy.can_switch_environment(viewer, strict=True) is False
    assert EnvironmentAccessPolicy.can_switch_environment(None, strict=True) is False


def test_credential_manager_token_masking():
    """CredentialManager must mask sensitive tokens in string representations."""
    mgr = CredentialManager()
    mgr.register_cluster_credentials(
        KubernetesCredentials(
            cluster_id="prod-cluster-01",
            cluster_name="prod-cluster-01",
            api_server_url="https://k8s.internal:6443",
            read_only_token="ey-secret-read-only-token-abc123xyz",
            remediation_token="ey-secret-remediation-token-danger999",
        )
    )

    creds = mgr.get_credentials("prod-cluster-01")
    assert creds is not None
    assert creds.read_only_token == "ey-secret-read-only-token-abc123xyz"
    assert creds.remediation_token == "ey-secret-remediation-token-danger999"

    # In string representations, tokens MUST be masked
    str_repr = str(creds)
    repr_repr = repr(creds)
    assert "abc123xyz" not in str_repr
    assert "danger999" not in str_repr
    assert "ey-s" in str_repr
    assert "abc123xyz" not in repr_repr
    assert "danger999" not in repr_repr
    CredentialManager.clear()


# ---------------------------------------------------------------------------
# 6. Data Isolation Context Tests
# ---------------------------------------------------------------------------

def test_cross_environment_data_isolation():
    """EnvironmentContext and get_current_data_source provide task-isolated tagging."""
    with EnvironmentContext.scope(EnvironmentMode.DEMOMESH):
        assert get_current_environment_mode() == EnvironmentMode.DEMOMESH
        assert get_current_data_source() == "SIMULATED"

    with EnvironmentContext.scope(EnvironmentMode.KUBERNETES):
        assert get_current_environment_mode() == EnvironmentMode.KUBERNETES
        assert get_current_data_source() == "LIVE_K8S"


# ---------------------------------------------------------------------------
# 7. FastAPI Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_environments_endpoints(client: AsyncClient):
    """Verifies all REST API routes for environment discovery and telemetry."""
    # Ensure environment manager is in clean DemoMesh mode
    await environment_manager.initialize()

    # 1. GET /api/v1/environments
    resp = await client.get("/api/v1/environments")
    assert resp.status_code == 200
    envs = resp.json()
    assert len(envs) >= 2
    modes = [e["mode"] for e in envs]
    assert "DEMOMESH" in modes
    assert "KUBERNETES" in modes

    # 2. GET /api/v1/environments/active
    resp = await client.get("/api/v1/environments/active")
    assert resp.status_code == 200
    active = resp.json()
    assert active["mode"] == "DEMOMESH"
    assert active["data_source"] == "SIMULATED"

    # 3. GET /api/v1/environments/health
    resp = await client.get("/api/v1/environments/health")
    assert resp.status_code == 200
    health = resp.json()
    assert health["mode"] == "DEMOMESH"
    assert health["is_healthy"] is True

    # 4. GET /api/v1/environments/services
    resp = await client.get("/api/v1/environments/services")
    assert resp.status_code == 200
    services = resp.json()
    assert len(services) > 0
    assert all(s["data_source"] == "SIMULATED" for s in services)

    # 5. GET /api/v1/environments/workloads
    resp = await client.get("/api/v1/environments/workloads")
    assert resp.status_code == 200
    workloads = resp.json()
    assert len(workloads) > 0

    # 6. GET /api/v1/environments/events
    resp = await client.get("/api/v1/environments/events?limit=5")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)

    # 7. GET /api/v1/environments/metrics
    resp = await client.get("/api/v1/environments/metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert isinstance(metrics, list)

    # 8. POST /api/v1/environments/select (switch to DEMOMESH explicitly)
    resp = await client.post("/api/v1/environments/select", json={"mode": "DEMOMESH"})
    assert resp.status_code == 200
    switch_data = resp.json()
    assert switch_data["active_mode"] == "DEMOMESH"
    assert switch_data["environment"]["data_source"] == "SIMULATED"
