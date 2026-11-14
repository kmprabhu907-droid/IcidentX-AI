"""
INCIDENTX AI - Kubernetes Infrastructure Investigator Agent (Phase 8.5)
Specialized agent for diagnosing container exit codes (137 OOMKilled, 1 CrashLoopBackOff),
pod restarts, unready deployments, node pressure taints, and Kubernetes warning events.
Seamlessly operates in both live Kubernetes clusters and simulated DemoMesh environments.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import EnvironmentMode
from backend.app.models.investigation import Evidence
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    KubernetesDiagnosticResult,
    KubernetesNodeDiagnostic,
    KubernetesPodDiagnostic,
)
from backend.app.services.observability.demo_mesh import demo_mesh


class KubernetesInvestigatorAgent(BaseInvestigationAgent):
    """
    Dedicated Kubernetes Infrastructure Investigator Agent.
    Collects container exit codes, crashloops, node pressure, and warning events,
    structuring them into court-grade Evidence items.
    """

    def __init__(self):
        super().__init__(
            name="KubernetesInvestigatorAgent",
            role="kubernetes",
            execution_phase="INFRASTRUCTURE_TRIAGE",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Executes deep container and cluster diagnostic analysis across active infrastructure.
        """
        now = datetime.now(timezone.utc)
        impact_scope = state.get("incident", {}).get("impact_scope", [])
        primary_service = impact_scope[0] if impact_scope else None

        active_mode = environment_manager.active_mode
        pod_diagnostics: List[KubernetesPodDiagnostic] = []
        node_diagnostics: List[KubernetesNodeDiagnostic] = []
        warning_events_count = 0
        oomkilled_count = 0
        crashloop_count = 0
        culprit_service: Optional[str] = None
        evidence_items: List[Evidence] = []
        is_cluster_reachable = True

        if active_mode == EnvironmentMode.KUBERNETES:
            # -----------------------------------------------------------------
            # Live Kubernetes Cluster Mode
            # -----------------------------------------------------------------
            try:
                adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
                if adapter and adapter.is_connected:
                    # 1. Fetch Pods with container status details
                    pods = await adapter.list_pods_detailed()
                    for pod in pods:
                        is_oom = "OOM" in (pod.phase or "") or pod.phase == "OOMKilled"
                        is_crash = "CrashLoop" in (pod.phase or "") or pod.restart_count >= 3
                        
                        exit_code = 137 if is_oom else (1 if is_crash else None)
                        exit_reason = "OOMKilled" if is_oom else ("CrashLoopBackOff" if is_crash else None)

                        if is_oom:
                            oomkilled_count += 1
                            culprit_service = pod.name
                        if is_crash:
                            crashloop_count += 1
                            if not culprit_service:
                                culprit_service = pod.name

                        p_diag = KubernetesPodDiagnostic(
                            pod_name=pod.name,
                            namespace=pod.namespace,
                            phase=pod.phase,
                            restart_count=pod.restart_count,
                            exit_code=exit_code,
                            exit_reason=exit_reason,
                            node_name=pod.node_name,
                            is_crashloop=is_crash,
                            is_oomkilled=is_oom,
                        )
                        pod_diagnostics.append(p_diag)

                        if is_oom or is_crash or pod.restart_count > 0:
                            evidence_items.append(
                                Evidence(
                                    id=str(uuid.uuid4()),
                                    incident_id=incident_id,
                                    evidence_type="K8S_CONTAINER_TERMINATION",
                                    source_system="kubernetes-kubelet",
                                    affected_service_name=pod.name,
                                    raw_source_ref=f"k8s://{pod.namespace}/pods/{pod.name}",
                                    description=(
                                        f"Container in Pod '{pod.name}' terminated. Reason: {exit_reason or 'Exit'} "
                                        f"(Exit Code: {exit_code or 'Unknown'}). Restarts: {pod.restart_count}."
                                    ),
                                    relevant_observation=(
                                        f"Pod phase: {pod.phase}. Node: {pod.node_name or 'unassigned'}. "
                                        f"OOMKilled={is_oom}, CrashLoop={is_crash}."
                                    ),
                                    confidence_score=0.96 if is_oom else 0.88,
                                    is_contradictory=False,
                                    verification_status="VERIFIED",
                                    observed_at=now,
                                )
                            )

                    # 2. Fetch Nodes
                    nodes = await adapter.list_nodes()
                    for node in nodes:
                        is_ready = getattr(node, "ready", True)
                        conditions = getattr(node, "conditions", {})
                        n_diag = KubernetesNodeDiagnostic(
                            node_name=node.name,
                            ready=is_ready,
                            memory_pressure=conditions.get("MemoryPressure") == "True",
                            disk_pressure=conditions.get("DiskPressure") == "True",
                            pid_pressure=conditions.get("PIDPressure") == "True",
                        )
                        node_diagnostics.append(n_diag)

                    # 3. Warning Events
                    events = await adapter.events.list_events(limit=25, only_warnings=True)
                    warning_events_count = len(events)
                    for ev in events:
                        conf = 0.95 if ev.reason in ["OOMKilled", "CrashLoopBackOff", "FailedScheduling"] else 0.82
                        evidence_items.append(
                            Evidence(
                                id=str(uuid.uuid4()),
                                incident_id=incident_id,
                                evidence_type="K8S_WARNING_EVENT",
                                source_system="kubernetes-apiserver",
                                affected_service_name=ev.resource_name,
                                raw_source_ref=f"k8s://{ev.namespace or 'default'}/events/{ev.id}",
                                description=f"Kubernetes [{ev.reason}]: {ev.message}",
                                relevant_observation=f"Event count: {ev.count}. First seen: {ev.first_timestamp}.",
                                confidence_score=conf,
                                is_contradictory=False,
                                verification_status="VERIFIED",
                                observed_at=now,
                            )
                        )
                else:
                    is_cluster_reachable = False
            except Exception as e:
                logger.warning(f"[{self.name}] Live Kubernetes inspection encountered error: {e}")
                is_cluster_reachable = False

        else:
            # -----------------------------------------------------------------
            # DemoMesh Simulation Mode
            # -----------------------------------------------------------------
            active_faults = getattr(demo_mesh, "active_faults", {})

            for svc_name in ["gateway-service", "order-service", "payment-service", "postgres-db", "auth-service"]:
                is_oom = "memory_leak" in active_faults and svc_name in ["order-service", "postgres-db"]
                is_crash = "service_outage" in active_faults and svc_name == "order-service"
                is_restarts = is_oom or is_crash

                restarts = 4 if is_oom else (6 if is_crash else 0)
                phase = "CrashLoopBackOff" if is_crash else ("OOMKilled" if is_oom else "Running")
                exit_code = 137 if is_oom else (1 if is_crash else 0)
                exit_reason = "OOMKilled" if is_oom else ("CrashLoopBackOff" if is_crash else None)

                if is_oom:
                    oomkilled_count += 1
                    culprit_service = svc_name
                if is_crash:
                    crashloop_count += 1
                    if not culprit_service:
                        culprit_service = svc_name

                p_diag = KubernetesPodDiagnostic(
                    pod_name=f"{svc_name}-7b9f5-x2",
                    namespace="production",
                    phase=phase,
                    restart_count=restarts,
                    exit_code=exit_code if is_restarts else None,
                    exit_reason=exit_reason,
                    node_name="worker-node-pool-1",
                    is_crashloop=is_crash,
                    is_oomkilled=is_oom,
                )
                pod_diagnostics.append(p_diag)

                if is_restarts:
                    evidence_items.append(
                        Evidence(
                            id=str(uuid.uuid4()),
                            incident_id=incident_id,
                            evidence_type="K8S_CONTAINER_TERMINATION",
                            source_system="demomesh-simulated-kubelet",
                            affected_service_name=svc_name,
                            raw_source_ref=f"demomesh://production/pods/{svc_name}-7b9f5-x2",
                            description=(
                                f"Simulated container '{svc_name}' terminated. Reason: {exit_reason} "
                                f"(Exit Code: {exit_code}). Restarts: {restarts}."
                            ),
                            relevant_observation=f"Demonstration simulation detected container failure on node 'worker-node-pool-1'.",
                            confidence_score=0.95,
                            is_contradictory=False,
                            verification_status="VERIFIED",
                            observed_at=now,
                        )
                    )

            # Node diagnostics for simulation
            node_diagnostics.append(
                KubernetesNodeDiagnostic(
                    node_name="worker-node-pool-1",
                    ready=True,
                    memory_pressure="memory_leak" in active_faults,
                    disk_pressure=False,
                    pid_pressure=False,
                )
            )

        # Persist collected evidence to database session
        for ev in evidence_items:
            session.add(ev)

        # Synthesize infrastructure summary
        if oomkilled_count > 0:
            summary = (
                f"Critical infrastructure anomaly detected: {oomkilled_count} container(s) terminated with "
                f"OOMKilled (Exit Code 137). Suspected memory exhaustion on '{culprit_service}'."
            )
        elif crashloop_count > 0:
            summary = (
                f"Infrastructure instability: {crashloop_count} pod(s) currently in CrashLoopBackOff. "
                f"Primary culprit workload: '{culprit_service}'."
            )
        else:
            summary = (
                f"Kubernetes cluster health nominal. {len(pod_diagnostics)} pods inspected, "
                f"zero OOMKills or CrashLoopBackOff anomalies detected."
            )

        result = KubernetesDiagnosticResult(
            environment_mode=active_mode.value,
            cluster_reachable=is_cluster_reachable,
            pod_diagnostics=pod_diagnostics,
            node_diagnostics=node_diagnostics,
            warning_events_count=warning_events_count,
            oomkilled_count=oomkilled_count,
            crashloop_count=crashloop_count,
            infrastructure_culprit_service=culprit_service,
            infrastructure_summary=summary,
        )

        state["kubernetes"] = result.model_dump()
        logger.info(f"[{self.name}] Completed diagnosis: {summary}")
        return state
