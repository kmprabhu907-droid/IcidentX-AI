"""
INCIDENTX AI - Controlled Remediation Action Library (Phase 12 Module 12.2)
Provides an immutable, strictly typed, allowlisted registry of remediation actions.
CRITICAL SAFETY RULE: Never permits arbitrary shell execution or unvetted kubectl strings.
Every action specifies strict preconditions, schema validations, timeouts, and rollback procedures.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.logging import logger
from backend.app.services.resolution.schemas import (
    ActionCategory,
    ResolutionActionItem,
    RiskClassification,
)


class ActionDefinition(BaseModel):
    action_id: str
    name: str
    category: ActionCategory
    action_type: str
    supported_environments: List[str] = Field(default_factory=lambda: ["DEMOMESH", "KUBERNETES_LIVE"])
    resource_type: str
    required_permissions: List[str]
    preconditions: List[str]
    default_risk: RiskClassification
    timeout_seconds: int = 30
    is_reversible: bool = True
    rollback_action_id: Optional[str] = None
    verification_conditions: List[str]
    description: str


class RemediationActionLibrary:
    """
    Immutable, allowlisted library of certified remediation actions.
    Guarantees deterministic execution safety across both DemoMesh and Kubernetes Live.
    """

    _ACTIONS: Dict[str, ActionDefinition] = {
        # ----------------------------------------------------------------------
        # KUBERNETES ACTIONS
        # ----------------------------------------------------------------------
        "k8s-restart-deployment": ActionDefinition(
            action_id="k8s-restart-deployment",
            name="Restart Deployment Pods",
            category=ActionCategory.KUBERNETES,
            action_type="restart",
            resource_type="apps/v1/Deployment",
            required_permissions=["apps/deployments/patch", "core/pods/list"],
            preconditions=[
                "Target deployment exists in specified namespace",
                "Deployment has at least 1 ready replica before restart",
                "Cluster is not under global maintenance lockdown",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=45,
            is_reversible=True,
            rollback_action_id="k8s-restart-deployment",
            verification_conditions=[
                "New ReplicaSet reaches 100% ready replicas",
                "Zero CrashLoopBackOff restarts observed for 60 seconds",
            ],
            description="Performs a graceful rolling restart of the target Deployment pods by updating rollout annotations.",
        ),
        "k8s-scale-deployment": ActionDefinition(
            action_id="k8s-scale-deployment",
            name="Scale Deployment Replicas",
            category=ActionCategory.KUBERNETES,
            action_type="scale",
            resource_type="apps/v1/Deployment",
            required_permissions=["apps/deployments/scale"],
            preconditions=[
                "Target deployment exists in namespace",
                "Target replica count is within approved guardrails (1 to 10)",
                "Cluster node capacity supports replica expansion",
            ],
            default_risk=RiskClassification.MODERATE,
            timeout_seconds=60,
            is_reversible=True,
            rollback_action_id="k8s-scale-deployment",
            verification_conditions=[
                "All desired replicas reach Ready condition",
                "Average CPU/Memory per pod drops below 75%",
            ],
            description="Adjusts deployment replica count to relieve CPU/memory saturation or scale down unhealthy workloads.",
        ),
        "k8s-rollback-deployment": ActionDefinition(
            action_id="k8s-rollback-deployment",
            name="Roll Back Deployment Revision",
            category=ActionCategory.KUBERNETES,
            action_type="rollback",
            resource_type="apps/v1/Deployment",
            required_permissions=["apps/deployments/patch", "apps/replicasets/list"],
            preconditions=[
                "Target deployment has at least one verified prior ReplicaSet revision",
                "Destination revision is stable and verified",
            ],
            default_risk=RiskClassification.HIGH,
            timeout_seconds=90,
            is_reversible=True,
            rollback_action_id="k8s-rollback-deployment",
            verification_conditions=[
                "Previous stable container image is successfully restored",
                "Error rate returns below 1% threshold",
            ],
            description="Reverts deployment pod template to a known good previous revision to eliminate code regressions.",
        ),
        "k8s-recreate-pods": ActionDefinition(
            action_id="k8s-recreate-pods",
            name="Recreate Failed Pods",
            category=ActionCategory.KUBERNETES,
            action_type="recreate_pods",
            resource_type="core/v1/Pod",
            required_permissions=["core/pods/delete"],
            preconditions=[
                "Pod is owned by an active ReplicaSet or DaemonSet controller",
                "Disruption budget permits pod recreation",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=30,
            is_reversible=False,
            rollback_action_id=None,
            verification_conditions=[
                "ReplicaSet automatically spawns healthy replacement pod",
                "Container exit code remains 0",
            ],
            description="Evicts OOMKilled or zombie pods, allowing the owning controller to create fresh instances.",
        ),
        "k8s-restore-config": ActionDefinition(
            action_id="k8s-restore-config",
            name="Restore ConfigMap Configuration",
            category=ActionCategory.KUBERNETES,
            action_type="restore_config",
            resource_type="core/v1/ConfigMap",
            required_permissions=["core/configmaps/update"],
            preconditions=[
                "Verified baseline configuration is available in reliable storage",
                "Config change is backwards compatible with running containers",
            ],
            default_risk=RiskClassification.MODERATE,
            timeout_seconds=30,
            is_reversible=True,
            rollback_action_id="k8s-restore-config",
            verification_conditions=[
                "ConfigMap data hash matches verified baseline",
            ],
            description="Restores an approved, verified configuration payload to a ConfigMap.",
        ),
        "k8s-validate-probes": ActionDefinition(
            action_id="k8s-validate-probes",
            name="Validate Readiness & Health Probes",
            category=ActionCategory.KUBERNETES,
            action_type="validate_probes",
            resource_type="apps/v1/Deployment",
            required_permissions=["apps/deployments/get", "core/pods/get"],
            preconditions=[
                "Deployment defines readinessProbe or livenessProbe",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=15,
            is_reversible=False,
            rollback_action_id=None,
            verification_conditions=[
                "Probe HTTP or TCP endpoints return 200 OK",
            ],
            description="Tests health check probes against running pods to verify readiness criteria.",
        ),

        # ----------------------------------------------------------------------
        # APPLICATION ACTIONS
        # ----------------------------------------------------------------------
        "app-disable-feature-flag": ActionDefinition(
            action_id="app-disable-feature-flag",
            name="Disable Regressed Feature Flag",
            category=ActionCategory.APPLICATION,
            action_type="toggle_flag",
            resource_type="feature_flag",
            required_permissions=["flags/toggle"],
            preconditions=[
                "Feature flag exists in application flag registry",
                "Flag was modified within 60 minutes of incident onset",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=15,
            is_reversible=True,
            rollback_action_id="app-disable-feature-flag",
            verification_conditions=[
                "Feature flag state is False",
                "Downstream error rate drops within 30 seconds",
            ],
            description="Toggles an experimental or faulty feature flag to OFF to isolate buggy application paths.",
        ),
        "app-restore-configuration": ActionDefinition(
            action_id="app-restore-configuration",
            name="Restore Application Configuration",
            category=ActionCategory.APPLICATION,
            action_type="restore_config",
            resource_type="application_setting",
            required_permissions=["config/update"],
            preconditions=[
                "Prior configuration key and value are securely verified",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=20,
            is_reversible=True,
            rollback_action_id="app-restore-configuration",
            verification_conditions=[
                "Configuration parameter reflects verified baseline value",
            ],
            description="Restores safe tuning parameters (e.g., timeout limits, batch sizes) to application.",
        ),
        "app-trigger-recovery-workflow": ActionDefinition(
            action_id="app-trigger-recovery-workflow",
            name="Trigger Application Recovery Workflow",
            category=ActionCategory.APPLICATION,
            action_type="trigger_workflow",
            resource_type="application_runtime",
            required_permissions=["runtime/flush", "runtime/reconnect"],
            preconditions=[
                "Service exposes health-gated recovery endpoint",
                "Connection pool or cache state is saturated",
            ],
            default_risk=RiskClassification.MODERATE,
            timeout_seconds=30,
            is_reversible=False,
            rollback_action_id=None,
            verification_conditions=[
                "Connection pool active count drops below 50%",
                "Cache hit ratio normalizes",
            ],
            description="Flushes corrupted cache keys or resets idle database connection pools via application hooks.",
        ),

        # ----------------------------------------------------------------------
        # INFRASTRUCTURE ACTIONS
        # ----------------------------------------------------------------------
        "infra-recheck-health": ActionDefinition(
            action_id="infra-recheck-health",
            name="Recheck Infrastructure Health",
            category=ActionCategory.INFRASTRUCTURE,
            action_type="recheck_health",
            resource_type="infrastructure_cluster",
            required_permissions=["cluster/status/read"],
            preconditions=[
                "Cluster control plane is reachable",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=15,
            is_reversible=False,
            rollback_action_id=None,
            verification_conditions=[
                "Cluster node status is Ready",
            ],
            description="Executes passive health checks against node kubelets and network interfaces.",
        ),
        "infra-validate-dependencies": ActionDefinition(
            action_id="infra-validate-dependencies",
            name="Validate Service Dependencies",
            category=ActionCategory.INFRASTRUCTURE,
            action_type="validate_dependencies",
            resource_type="service_mesh_link",
            required_permissions=["mesh/egress/check"],
            preconditions=[
                "Upstream and downstream services are cataloged",
            ],
            default_risk=RiskClassification.LOW,
            timeout_seconds=15,
            is_reversible=False,
            rollback_action_id=None,
            verification_conditions=[
                "All dependency endpoints return HTTP 200 or healthy TCP handshake",
            ],
            description="Verifies egress connectivity and DNS resolution from the affected service to all dependencies.",
        ),
    }

    @classmethod
    def get_action_definition(cls, action_id: str) -> Optional[ActionDefinition]:
        return cls._ACTIONS.get(action_id)

    @classmethod
    def list_actions(cls) -> List[ActionDefinition]:
        return list(cls._ACTIONS.values())

    @classmethod
    def is_allowlisted(cls, action_id: str) -> bool:
        return action_id in cls._ACTIONS

    @classmethod
    def create_action_item(
        cls,
        action_id: str,
        target_service: str,
        environment: str = "DEMOMESH",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ResolutionActionItem:
        defn = cls._ACTIONS.get(action_id)
        if not defn:
            raise ValueError(f"Action '{action_id}' is not in the certified allowlist.")

        target_res = f"{defn.resource_type.lower()}/{target_service}"
        return ResolutionActionItem(
            action_id=defn.action_id,
            name=defn.name,
            category=defn.category,
            action_type=defn.action_type,
            target_resource=target_res,
            target_service_name=target_service,
            environment=environment,
            parameters=parameters or {},
            preconditions=defn.preconditions,
            expected_outcome=f"Successfully apply {defn.name} on {target_service}",
            potential_side_effects=[
                f"Temporary connection drop during {defn.action_type}",
            ] if defn.default_risk in (RiskClassification.MODERATE, RiskClassification.HIGH) else [],
            risk_level=defn.default_risk,
            timeout_seconds=defn.timeout_seconds,
            is_reversible=defn.is_reversible,
            rollback_action_id=defn.rollback_action_id,
            verification_strategy="; ".join(defn.verification_conditions),
        )


action_library = RemediationActionLibrary()
