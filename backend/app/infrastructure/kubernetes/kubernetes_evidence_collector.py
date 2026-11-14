"""
INCIDENTX AI - Kubernetes Evidence Collector (Phase 8.2)
Translates live Kubernetes pod restart loops, OOM conditions, degraded deployments,
and warning events into standardized Evidence objects for the 10-Agent Investigation Pipeline.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentMode,
    InfrastructureEvent,
    KubernetesDeployment,
    KubernetesPod,
)
from backend.app.infrastructure.kubernetes.kubernetes_adapter import KubernetesAdapter
from backend.app.models.investigation import Evidence


class KubernetesEvidenceCollector:
    """Collects live infrastructure signals and structures them as court-grade Evidence."""

    @classmethod
    async def collect_incident_evidence(
        cls,
        incident_id: str,
        target_service: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> List[Evidence]:
        """
        Discovers active anomalies on live Kubernetes cluster and builds Evidence models.
        Strictly applies data_source = 'LIVE_K8S' to preserve environment isolation.
        """
        if environment_manager.active_mode != EnvironmentMode.KUBERNETES:
            return []

        adapter = environment_manager.registry.get_adapter(EnvironmentMode.KUBERNETES)
        if not isinstance(adapter, KubernetesAdapter) or not adapter.is_connected:
            return []

        evidence_items: List[Evidence] = []
        now = datetime.now(timezone.utc)

        try:
            # 1. Inspect Pods for Restarts and Crash Loops
            pods: List[KubernetesPod] = await adapter.list_pods_detailed(namespace=namespace)
            for pod in pods:
                if target_service and target_service not in pod.name:
                    continue

                if pod.restart_count > 0 or pod.phase in ["CrashLoopBackOff", "Failed", "OOMKilled"]:
                    sev_score = 0.95 if "OOM" in pod.phase or pod.restart_count >= 3 else 0.80
                    evidence_items.append(
                        Evidence(
                            id=str(uuid.uuid4()),
                            incident_id=incident_id,
                            evidence_type="K8S_POD_FAILURE",
                            source_system="kubernetes-kubelet",
                            affected_service_name=pod.name,
                            raw_source_ref=f"k8s://{pod.namespace}/pods/{pod.name}",
                            description=f"Pod '{pod.name}' in namespace '{pod.namespace}' is in phase '{pod.phase}' with {pod.restart_count} container restarts.",
                            relevant_observation=f"Container restart count surged to {pod.restart_count}. Pod IP: {pod.pod_ip or 'None'}, Node: {pod.node_name or 'Unassigned'}.",
                            confidence_score=sev_score,
                            is_contradictory=False,
                            observed_at=now,
                        )
                    )

            # 2. Inspect Warning Events
            events: List[InfrastructureEvent] = await adapter.events.list_events(
                namespace=namespace, limit=20, only_warnings=True
            )
            for ev in events:
                if target_service and target_service not in ev.resource_name:
                    continue

                conf = 0.95 if ev.reason in ["OOMKilled", "CrashLoopBackOff"] else 0.85
                evidence_items.append(
                    Evidence(
                        id=str(uuid.uuid4()),
                        incident_id=incident_id,
                        evidence_type="K8S_EVENT_ANOMALY",
                        source_system="kubernetes-events",
                        affected_service_name=ev.resource_name,
                        raw_source_ref=f"k8s://{ev.namespace or 'default'}/events/{ev.id}",
                        description=f"Kubernetes Warning Event [{ev.reason}]: {ev.message}",
                        relevant_observation=f"Event type: {ev.event_type}, Reason: {ev.reason}, Component: {ev.source_component}, Occurrences: {ev.count}",
                        confidence_score=conf,
                        is_contradictory=False,
                        observed_at=now,
                    )
                )

            # 3. Inspect Degraded Deployments
            deployments: List[KubernetesDeployment] = await adapter.list_deployments_detailed(namespace=namespace)
            for dep in deployments:
                if target_service and target_service not in dep.name:
                    continue

                if dep.rollout_status in ["Degraded", "Progressing"] or dep.available_replicas < dep.desired_replicas:
                    evidence_items.append(
                        Evidence(
                            id=str(uuid.uuid4()),
                            incident_id=incident_id,
                            evidence_type="K8S_DEPLOYMENT_DEGRADED",
                            source_system="kubernetes-controller-manager",
                            affected_service_name=dep.name,
                            raw_source_ref=f"k8s://{dep.namespace}/deployments/{dep.name}",
                            description=f"Deployment '{dep.name}' replica deficit: {dep.available_replicas}/{dep.desired_replicas} available. Status: {dep.rollout_status}.",
                            relevant_observation=f"Rollout status '{dep.rollout_status}', updated replicas: {dep.updated_replicas}.",
                            confidence_score=0.90,
                            is_contradictory=False,
                            observed_at=now,
                        )
                    )

        except Exception as e:
            # Safe degradation: do not break investigation if K8s query fails
            pass

        return evidence_items
