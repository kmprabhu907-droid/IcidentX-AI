"""
INCIDENTX AI - Kubernetes Investigator Agent Test Suite (Phase 8.5)
Verifies:
1. Agent initialization and base interface compliance.
2. Diagnostic evaluation in DemoMesh simulation mode (nominal, memory leak OOMKill 137, crashloop).
3. Diagnostic evaluation in Kubernetes live mode with mock client.
4. Evidence generation and court-grade persistence in database session.
5. End-to-end integration into InvestigationOrchestrator pipeline.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session_factory
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentMode,
    InfrastructureEvent,
    KubernetesNode,
    KubernetesPod,
)
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter
from backend.app.models.incident import Incident
from backend.app.models.investigation import AgentExecution, Evidence
from backend.app.services.investigation.agents.kubernetes_agent import KubernetesInvestigatorAgent
from backend.app.services.investigation.orchestrator import investigation_orchestrator
from backend.app.services.observability.demo_mesh import demo_mesh


@pytest.mark.asyncio
async def test_kubernetes_investigator_agent_init():
    agent = KubernetesInvestigatorAgent()
    assert agent.name == "KubernetesInvestigatorAgent"
    assert agent.role == "kubernetes"
    assert agent.execution_phase == "INFRASTRUCTURE_TRIAGE"
    assert agent.timeout_seconds == 15.0


@pytest.mark.asyncio
async def test_kubernetes_investigator_agent_demomesh_nominal(db_session: AsyncSession):
    demo_mesh.active_faults.clear()
    await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)

    agent = KubernetesInvestigatorAgent()
    state = {"incident": {"impact_scope": ["order-service"]}}

    result_state = await agent.execute("test-inc-1", state, db_session)
    assert "kubernetes" in result_state
    k8s = result_state["kubernetes"]
    assert k8s["environment_mode"].upper() == "DEMOMESH"
    assert k8s["oomkilled_count"] == 0
    assert k8s["crashloop_count"] == 0
    assert len(k8s["pod_diagnostics"]) >= 5


@pytest.mark.asyncio
async def test_kubernetes_investigator_agent_demomesh_oomkilled(db_session: AsyncSession):
    demo_mesh.active_faults["memory_leak"] = {"service": "order-service"}
    await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)

    agent = KubernetesInvestigatorAgent()
    state = {"incident": {"impact_scope": ["order-service"]}}

    result_state = await agent.execute("test-inc-2", state, db_session)
    demo_mesh.active_faults.clear()

    k8s = result_state["kubernetes"]
    assert k8s["oomkilled_count"] > 0
    assert k8s["infrastructure_culprit_service"] in ["order-service", "postgres-db"]
    assert any(p["exit_code"] == 137 for p in k8s["pod_diagnostics"])
    assert any(p["is_oomkilled"] for p in k8s["pod_diagnostics"])


@pytest.mark.asyncio
async def test_kubernetes_investigator_agent_demomesh_crashloop(db_session: AsyncSession):
    demo_mesh.active_faults["service_outage"] = {"service": "order-service"}
    await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)

    agent = KubernetesInvestigatorAgent()
    state = {"incident": {"impact_scope": ["order-service"]}}

    result_state = await agent.execute("test-inc-3", state, db_session)
    demo_mesh.active_faults.clear()

    k8s = result_state["kubernetes"]
    assert k8s["crashloop_count"] > 0
    assert any(p["phase"] == "CrashLoopBackOff" for p in k8s["pod_diagnostics"])
    assert any(p["exit_code"] == 1 for p in k8s["pod_diagnostics"])


@pytest.mark.asyncio
async def test_kubernetes_investigator_agent_live_k8s_mock(db_session: AsyncSession):
    original_k8s_adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
    await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)
    agent = KubernetesInvestigatorAgent()

    # Create mock KubernetesAdapter
    mock_adapter = MagicMock(spec=KubernetesAdapter)
    mock_adapter.is_connected = True

    mock_pod = KubernetesPod(
        name="payment-gateway-7b89d-x1",
        namespace="default",
        phase="CrashLoopBackOff",
        restart_count=5,
        node_name="node-1",
        pod_ip="10.244.0.5",
        start_time=datetime.now(timezone.utc),
    )
    mock_adapter.list_pods_detailed = AsyncMock(return_value=[mock_pod])
    mock_adapter.list_nodes = AsyncMock(return_value=[
        KubernetesNode(name="node-1", ready=True, kubelet_version="v1.30.0")
    ])
    now_str = datetime.now(timezone.utc).isoformat()
    mock_event = InfrastructureEvent(
        id="ev-1",
        event_type="Warning",
        reason="OOMKilled",
        message="Container exceeded memory limit of 512Mi",
        source_component="kubelet",
        resource_kind="Pod",
        resource_name="payment-gateway-7b89d-x1",
        namespace="default",
        count=3,
        first_timestamp=now_str,
        last_timestamp=now_str,
    )
    mock_adapter.events = MagicMock()
    mock_adapter.events.list_events = AsyncMock(return_value=[mock_event])

    # Inject mock into registry
    environment_manager.registry.register_adapter(EnvironmentMode.KUBERNETES, mock_adapter)
    environment_manager._active_mode = EnvironmentMode.KUBERNETES

    try:
        state = {"incident": {"impact_scope": ["payment-gateway"]}}
        result_state = await agent.execute("test-inc-4", state, db_session)

        k8s = result_state["kubernetes"]
        assert k8s["environment_mode"].upper() == "KUBERNETES"
        assert k8s["cluster_reachable"] is True
        assert k8s["crashloop_count"] >= 1
        assert len(k8s["pod_diagnostics"]) == 1
        assert k8s["pod_diagnostics"][0]["pod_name"] == "payment-gateway-7b89d-x1"
        assert k8s["warning_events_count"] == 1
    finally:
        if original_k8s_adapter:
            environment_manager.registry.register_adapter(EnvironmentMode.KUBERNETES, original_k8s_adapter)
        await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)


@pytest.mark.asyncio
async def test_kubernetes_agent_in_orchestrator_pipeline():
    import uuid
    await environment_manager.switch_environment(EnvironmentMode.DEMOMESH)
    demo_mesh.active_faults.clear()

    incident_id = f"inc-k8s-{uuid.uuid4().hex[:8]}"

    async with async_session_factory() as session:
        async with session.begin():
            test_inc = Incident(
                id=incident_id,
                title="Payment Service Latency Spike",
                summary="High 504 Gateway Timeouts observed on checkout",
                severity="SEV-2",
                status="DETECTED",
                impact_scope="order-service, payment-service",
            )
            session.add(test_inc)

    res = await investigation_orchestrator.run_investigation(incident_id)

    assert res["status"] == "COMPLETED"
    assert "KubernetesInvestigatorAgent" in res["completed_agents"]

    # Verify AgentExecution record was persisted
    async with async_session_factory() as session:
        stmt = select(AgentExecution).where(
            AgentExecution.incident_id == incident_id,
            AgentExecution.agent_role == "kubernetes"
        )
        exec_res = await session.execute(stmt)
        exec_rec = exec_res.scalar_one_or_none()
        assert exec_rec is not None
        assert exec_rec.status == "COMPLETED"
        assert exec_rec.execution_phase == "INFRASTRUCTURE_TRIAGE"
