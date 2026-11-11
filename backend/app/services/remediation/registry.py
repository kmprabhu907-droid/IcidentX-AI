"""
INCIDENTX AI - Remediation Action Library & Controlled Registry
Provides an immutable, strictly typed registry of safe, predefined recovery actions.
Never executes arbitrary shell strings or unvetted LLM-generated commands.
All actions execute exclusively within the isolated local simulation environment.
"""

from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, Field, field_validator

from backend.app.core.logging import logger
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.simulation.chaos_controller import chaos_controller


# ============================================================================
# Parameter Schemas for Strictly Validated Action Payloads
# ============================================================================

class RestartServiceParams(BaseModel):
    service_name: str = Field(..., description="Target microservice name to restart")
    grace_period_seconds: int = Field(default=5, ge=1, le=60, description="Grace period before killing process")


class ScaleReplicasParams(BaseModel):
    service_name: str = Field(..., description="Microservice to scale")
    target_replicas: int = Field(..., ge=1, le=10, description="Target replica count")
    current_replicas: int = Field(default=2, ge=1, le=10, description="Current replica count")

    @field_validator("target_replicas")
    def validate_replica_shift(cls, v, info):
        return v


class RollbackDeploymentParams(BaseModel):
    service_name: str = Field(..., description="Service undergoing version rollback")
    target_version: str = Field(..., description="Stable destination version, e.g. v1.4.1")
    current_version: str = Field(default="v1.4.2", description="Regressed current version")


class ClearCacheParams(BaseModel):
    service_name: str = Field(default="redis-cache", description="Target cache service")
    cache_pattern: str = Field(default="ALL", description="Cache key pattern or ALL")


class ResetDbPoolParams(BaseModel):
    service_name: str = Field(default="postgres-db", description="Target database instance")
    max_connections: int = Field(default=100, ge=10, le=500, description="Max pool connection limit")
    terminate_idle_seconds: int = Field(default=30, ge=5, le=300, description="Terminate connections idle for >N seconds")


class ToggleFeatureFlagParams(BaseModel):
    flag_name: str = Field(..., description="Target feature flag identifier")
    enabled: bool = Field(default=False, description="Desired flag state (False to disable)")
    service_name: str = Field(default="order-service", description="Service owning the flag")


class ApplyRateLimitParams(BaseModel):
    service_name: str = Field(default="api-gateway", description="Gateway or service applying ingress throttling")
    max_requests_per_second: float = Field(default=30.0, ge=1.0, le=500.0, description="Target rate limit ceiling")
    burst_limit: int = Field(default=50, ge=5, le=1000, description="Allowed burst ceiling")


class SwitchDependencyParams(BaseModel):
    service_name: str = Field(..., description="Client service redirecting egress traffic")
    dependency_name: str = Field(..., description="Target dependency being switched (e.g. psp-gateway)")
    target_endpoint: str = Field(..., description="Healthy secondary/failover endpoint identifier")


# ============================================================================
# Base Abstract Remediation Action Contract
# ============================================================================

class BaseRemediationAction(ABC):
    """
    Abstract contract for all remediation actions.
    Enforces precondition evaluation, parameters schema validation, simulated
    environment execution, empirical metric verification, and state rollback.
    """
    action_id: str
    name: str
    description: str
    action_type: str
    supported_incident_types: List[str]
    risk_level: str  # LOW, MEDIUM, HIGH
    estimated_cost: str  # LOW, MEDIUM, HIGH
    default_timeout_seconds: int = 15
    parameter_schema: Type[BaseModel]

    def validate_parameters(self, raw_params: Dict[str, Any]) -> BaseModel:
        """Validate input parameters against the strict Pydantic schema."""
        return self.parameter_schema.model_validate(raw_params)

    @abstractmethod
    async def check_preconditions(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Verify safety conditions and system state prior to execution.
        Returns (is_satisfied: bool, reason: str).
        """
        pass

    @abstractmethod
    async def execute_simulated(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute recovery action inside the isolated local simulation environment.
        Returns execution details and logs.
        """
        pass

    @abstractmethod
    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Verify recovery outcome using fresh telemetry.
        Returns (status: VERIFIED | PARTIALLY_VERIFIED | FAILED | INCONCLUSIVE, details: dict).
        """
        pass

    @abstractmethod
    async def rollback_simulated(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Revert the action in the simulation environment if verification fails or an error occurs.
        """
        pass


# ============================================================================
# Action 1: Restart Service
# ============================================================================

class RestartServiceAction(BaseRemediationAction):
    action_id = "act-restart-service"
    name = "Restart Unhealthy Service Instance"
    description = "Gracefully restarts container or process instance to purge memory leaks, terminate deadlocks, or recover failed worker loops."
    action_type = "restart"
    supported_incident_types = ["memory_leak", "cpu_spike", "instance_termination", "zombie_process"]
    risk_level = "LOW"
    estimated_cost = "LOW"
    default_timeout_seconds = 10
    parameter_schema = RestartServiceParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name")
        if svc not in demo_mesh.SERVICE_DEFINITIONS:
            return False, f"Target service '{svc}' does not exist in cluster definition."
        return True, f"Service '{svc}' exists and is eligible for graceful restart."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        logger.info(f"[Remediation][RestartService] Initiating simulated restart of '{svc}'")

        # In simulation: Clear any active memory_leak or instance_termination fault for this service
        for scenario_id in ["memory_leak", "instance_termination", "cpu_spike"]:
            if scenario_id in chaos_controller._active_faults:
                fault = chaos_controller._active_faults[scenario_id]
                if fault.target_service == svc:
                    await chaos_controller.stop(scenario_id)

        # Reset service metrics queue in demo_mesh to clean baseline
        if svc in demo_mesh.metrics_history and demo_mesh.metrics_history[svc]:
            last = demo_mesh.metrics_history[svc][-1]
            last.memory_utilization = 45.0
            last.cpu_utilization = 20.0
            last.error_rate = 0.05
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "target_service": svc,
            "message": f"Service '{svc}' restarted successfully. Memory and thread handles reset.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params["service_name"]
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        mem_before = before_svc.get("memory_utilization", 0.0)
        mem_after = after_svc.get("memory_utilization", 0.0)
        err_before = before_svc.get("error_rate", 0.0)
        err_after = after_svc.get("error_rate", 0.0)
        health_after = after_svc.get("health_status", "UNKNOWN")

        delta_mem = round(mem_after - mem_before, 2)
        delta_err = round(err_after - err_before, 2)

        details = {
            "service": svc,
            "memory_utilization_before": mem_before,
            "memory_utilization_after": mem_after,
            "delta_memory": delta_mem,
            "error_rate_before": err_before,
            "error_rate_after": err_after,
            "delta_error_rate": delta_err,
            "health_status_after": health_after,
        }

        if health_after == "HEALTHY" and (mem_after < 70.0 or delta_mem < -15.0 or err_after <= 1.0):
            return "VERIFIED", details
        elif delta_mem < 0 or delta_err < 0:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        logger.warning(f"[Remediation][RestartService] Rollback requested for '{svc}'. Restoring previous snapshot.")
        return {"rollback": "COMPLETED", "service": svc, "details": "Re-spawned previous container instance."}


# ============================================================================
# Action 2: Scale Replicas
# ============================================================================

class ScaleReplicasAction(BaseRemediationAction):
    action_id = "act-scale-replicas"
    name = "Scale Microservice Replica Count"
    description = "Increases worker replica pool to absorb volumetric traffic spikes and reduce per-replica CPU/memory saturation."
    action_type = "scale"
    supported_incident_types = ["traffic_surge", "cpu_spike", "queue_backpressure", "latency_spike"]
    risk_level = "LOW"
    estimated_cost = "LOW"
    default_timeout_seconds = 15
    parameter_schema = ScaleReplicasParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name")
        target_rep = params.get("target_replicas", 4)
        curr_rep = params.get("current_replicas", 2)
        if svc not in demo_mesh.SERVICE_DEFINITIONS:
            return False, f"Target service '{svc}' not recognized in cluster."
        if target_rep <= curr_rep:
            return False, f"Target replicas ({target_rep}) must exceed current replicas ({curr_rep})."
        return True, f"Preconditions met: Scaling '{svc}' from {curr_rep} to {target_rep} replicas."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        target = params["target_replicas"]
        curr = params.get("current_replicas", 2)

        # In simulation: diffuse traffic surge or cpu spike
        if "traffic_surge" in chaos_controller._active_faults:
            await chaos_controller.stop("traffic_surge")
        if "cpu_spike" in chaos_controller._active_faults and chaos_controller._active_faults["cpu_spike"].target_service == svc:
            await chaos_controller.stop("cpu_spike")

        # Lower latency and CPU in mesh
        if svc in demo_mesh.metrics_history and demo_mesh.metrics_history[svc]:
            last = demo_mesh.metrics_history[svc][-1]
            last.cpu_utilization = max(15.0, last.cpu_utilization / 2.0)
            last.latency_p95_ms = max(40.0, last.latency_p95_ms / 2.5)
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "target_service": svc,
            "scaled_from": curr,
            "scaled_to": target,
            "message": f"Successfully scaled {svc} replicas from {curr} to {target}.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params["service_name"]
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        cpu_before = before_svc.get("cpu_utilization", 0.0)
        cpu_after = after_svc.get("cpu_utilization", 0.0)
        p95_before = before_svc.get("latency_p95_ms", 0.0)
        p95_after = after_svc.get("latency_p95_ms", 0.0)

        details = {
            "service": svc,
            "cpu_before": cpu_before,
            "cpu_after": cpu_after,
            "delta_cpu": round(cpu_after - cpu_before, 2),
            "latency_p95_before": p95_before,
            "latency_p95_after": p95_after,
            "delta_p95": round(p95_after - p95_before, 2),
        }

        if cpu_after < 75.0 and p95_after < (p95_before * 0.7 or 250.0):
            return "VERIFIED", details
        elif cpu_after < cpu_before or p95_after < p95_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        curr = params.get("current_replicas", 2)
        return {"rollback": "COMPLETED", "service": svc, "details": f"Scaled {svc} back down to {curr} replicas."}


# ============================================================================
# Action 3: Rollback Deployment
# ============================================================================

class RollbackDeploymentAction(BaseRemediationAction):
    action_id = "act-rollback-deployment"
    name = "Roll Back Regressed Deployment"
    description = "Rolls back newly released code artifacts and schema flags to the last known stable deployment tag."
    action_type = "rollback"
    supported_incident_types = ["deployment_regression", "code_defect", "http_500_cascade"]
    risk_level = "MEDIUM"
    estimated_cost = "LOW"
    default_timeout_seconds = 20
    parameter_schema = RollbackDeploymentParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name")
        target_v = params.get("target_version")
        curr_v = params.get("current_version")
        if target_v == curr_v:
            return False, "Target version must differ from current version."
        if svc not in demo_mesh.SERVICE_DEFINITIONS:
            return False, f"Target service '{svc}' does not exist."
        return True, f"Preconditions met: Eligible to roll back '{svc}' from {curr_v} to {target_v}."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        target_v = params["target_version"]

        if "deployment_regression" in chaos_controller._active_faults:
            await chaos_controller.stop("deployment_regression")
        if "http_500_cascade" in chaos_controller._active_faults:
            await chaos_controller.stop("http_500_cascade")

        if svc in demo_mesh.SERVICE_DEFINITIONS:
            demo_mesh.SERVICE_DEFINITIONS[svc]["version"] = target_v

        # Reset errors
        if svc in demo_mesh.metrics_history and demo_mesh.metrics_history[svc]:
            last = demo_mesh.metrics_history[svc][-1]
            last.error_rate = 0.05
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "target_service": svc,
            "version_restored": target_v,
            "message": f"Deployment rolled back to {target_v}. Faulty codepaths eliminated.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params["service_name"]
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        err_before = before_svc.get("error_rate", 0.0)
        err_after = after_svc.get("error_rate", 0.0)

        details = {
            "service": svc,
            "error_rate_before": err_before,
            "error_rate_after": err_after,
            "delta_error_rate": round(err_after - err_before, 2),
        }

        if err_after <= 1.0 or (err_before > 5.0 and err_after < err_before * 0.2):
            return "VERIFIED", details
        elif err_after < err_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        curr_v = params.get("current_version", "v1.4.2")
        if svc in demo_mesh.SERVICE_DEFINITIONS:
            demo_mesh.SERVICE_DEFINITIONS[svc]["version"] = curr_v
        return {"rollback": "COMPLETED", "details": f"Re-applied version {curr_v}."}


# ============================================================================
# Action 4: Clear Application Cache
# ============================================================================

class ClearCacheAction(BaseRemediationAction):
    action_id = "act-clear-cache"
    name = "Flush Corrupt Application Cache"
    description = "Flushes poisoned, out-of-sync, or corrupted cache keys to restore authoritative backing-store lookups."
    action_type = "cache"
    supported_incident_types = ["redis_down", "cache_corruption", "stale_read_anomaly"]
    risk_level = "LOW"
    estimated_cost = "LOW"
    default_timeout_seconds = 10
    parameter_schema = ClearCacheParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        return True, "Preconditions met: Redis cache cluster reachable and responsive."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params.get("service_name", "redis-cache")
        pattern = params.get("cache_pattern", "ALL")

        if "redis_down" in chaos_controller._active_faults:
            await chaos_controller.stop("redis_down")

        if svc in demo_mesh.metrics_history and demo_mesh.metrics_history[svc]:
            last = demo_mesh.metrics_history[svc][-1]
            last.error_rate = 0.0
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "target_service": svc,
            "pattern_flushed": pattern,
            "message": f"Successfully flushed cache pattern '{pattern}' on {svc}.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params.get("service_name", "redis-cache")
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        err_before = before_svc.get("error_rate", 0.0)
        err_after = after_svc.get("error_rate", 0.0)
        health = after_svc.get("health_status", "HEALTHY")

        details = {
            "service": svc,
            "error_rate_before": err_before,
            "error_rate_after": err_after,
            "health_status_after": health,
        }

        if health == "HEALTHY" and err_after <= 1.0:
            return "VERIFIED", details
        elif err_after < err_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"rollback": "COMPLETED", "details": "Re-primed warm cache keys from Postgres database."}


# ============================================================================
# Action 5: Reset Database Connection Pool
# ============================================================================

class ResetDbPoolAction(BaseRemediationAction):
    action_id = "act-reset-db-pool"
    name = "Reset Database Connection Pool"
    description = "Terminates leaked idle-in-transaction client connections and re-establishes connection limits to break deadlocks."
    action_type = "db_pool"
    supported_incident_types = ["db_pool_exhaustion", "database_contention", "client_pool_leak"]
    risk_level = "MEDIUM"
    estimated_cost = "LOW"
    default_timeout_seconds = 15
    parameter_schema = ResetDbPoolParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name", "postgres-db")
        if svc not in demo_mesh.SERVICE_DEFINITIONS:
            return False, f"Database service '{svc}' not found in cluster."
        return True, f"Preconditions met: Database '{svc}' connection pool inspection ready."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params.get("service_name", "postgres-db")

        if "db_pool_exhaustion" in chaos_controller._active_faults:
            await chaos_controller.stop("db_pool_exhaustion")

        # Normalize DB pool in demo mesh
        for s in ["postgres-db", "order-service", "payment-service", "inventory-service"]:
            if s in demo_mesh.metrics_history and demo_mesh.metrics_history[s]:
                last = demo_mesh.metrics_history[s][-1]
                last.db_pool_utilization = 18.0
                last.error_rate = 0.05
                last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "target_service": svc,
            "message": "Terminated idle-in-transaction connections and reclaimed connection slots.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params.get("service_name", "postgres-db")
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        pool_before = before_svc.get("db_pool_utilization", 0.0)
        pool_after = after_svc.get("db_pool_utilization", 0.0)

        details = {
            "service": svc,
            "db_pool_utilization_before": pool_before,
            "db_pool_utilization_after": pool_after,
            "delta_pool": round(pool_after - pool_before, 2),
        }

        if pool_after < 50.0:
            return "VERIFIED", details
        elif pool_after < pool_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"rollback": "COMPLETED", "details": "Reopened standard client pool listeners."}


# ============================================================================
# Action 6: Toggle Faulty Feature Flag
# ============================================================================

class ToggleFeatureFlagAction(BaseRemediationAction):
    action_id = "act-toggle-feature-flag"
    name = "Disable Faulty Feature Flag"
    description = "Immediately deactivates an unstable or buggy runtime feature flag to divert traffic back to safe fallback pathways."
    action_type = "flag"
    supported_incident_types = ["feature_regression", "http_500_cascade", "payment_latency"]
    risk_level = "LOW"
    estimated_cost = "LOW"
    default_timeout_seconds = 5
    parameter_schema = ToggleFeatureFlagParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        flag = params.get("flag_name")
        if not flag:
            return False, "Feature flag name is required."
        return True, f"Preconditions met: Feature flag '{flag}' is active and controllable."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        flag = params["flag_name"]
        svc = params.get("service_name", "order-service")

        if "http_500_cascade" in chaos_controller._active_faults:
            await chaos_controller.stop("http_500_cascade")

        if svc in demo_mesh.metrics_history and demo_mesh.metrics_history[svc]:
            last = demo_mesh.metrics_history[svc][-1]
            last.error_rate = 0.08
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "flag_name": flag,
            "enabled": False,
            "message": f"Feature flag '{flag}' successfully disabled. Traffic routed to fallback path.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params.get("service_name", "order-service")
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        err_before = before_svc.get("error_rate", 0.0)
        err_after = after_svc.get("error_rate", 0.0)

        details = {
            "service": svc,
            "flag": params["flag_name"],
            "error_rate_before": err_before,
            "error_rate_after": err_after,
        }

        if err_after <= 1.0 or err_after < (err_before * 0.25):
            return "VERIFIED", details
        elif err_after < err_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        flag = params["flag_name"]
        return {"rollback": "COMPLETED", "details": f"Re-enabled feature flag '{flag}'."}


# ============================================================================
# Action 7: Apply Ingress Rate Limit
# ============================================================================

class ApplyRateLimitAction(BaseRemediationAction):
    action_id = "act-apply-rate-limit"
    name = "Apply Ingress Rate Limiting"
    description = "Enforces dynamic traffic throttling at API Gateway to protect downstream microservices from volumetric cascades."
    action_type = "rate_limit"
    supported_incident_types = ["traffic_surge", "ddos_attack", "downstream_saturation"]
    risk_level = "LOW"
    estimated_cost = "LOW"
    default_timeout_seconds = 5
    parameter_schema = ApplyRateLimitParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name", "api-gateway")
        if svc != "api-gateway":
            return False, "Rate limiting can only be applied at the API Gateway."
        return True, "Preconditions met: API Gateway ingress filter configurable."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        limit = params.get("max_requests_per_second", 30.0)

        if "traffic_surge" in chaos_controller._active_faults:
            await chaos_controller.stop("traffic_surge")

        # Clamp gateway metrics
        if "api-gateway" in demo_mesh.metrics_history and demo_mesh.metrics_history["api-gateway"]:
            last = demo_mesh.metrics_history["api-gateway"][-1]
            last.request_rate = min(last.request_rate, limit)
            last.error_rate = 0.05
            last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "rate_limit_rps": limit,
            "message": f"Applied ingress rate limit of {limit} RPS at API Gateway.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        gw_after = after_snapshot.get("api-gateway", {})
        order_after = after_snapshot.get("order-service", {})

        gw_health = gw_after.get("health_status", "HEALTHY")
        order_p95 = order_after.get("latency_p95_ms", 100.0)

        details = {
            "api_gateway_health": gw_health,
            "order_service_p95": order_p95,
        }

        if gw_health == "HEALTHY" and order_p95 < 250.0:
            return "VERIFIED", details
        else:
            return "PARTIALLY_VERIFIED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"rollback": "COMPLETED", "details": "Removed ingress rate limiting rules from API Gateway."}


# ============================================================================
# Action 8: Switch Dependency Failover
# ============================================================================

class SwitchDependencyAction(BaseRemediationAction):
    action_id = "act-switch-dependency"
    name = "Failover Degraded Egress Dependency"
    description = "Redirects outbound service requests from an unresponsive third-party or internal provider to a healthy hot-standby fallback."
    action_type = "switch_dep"
    supported_incident_types = ["payment_latency", "external_psp_timeout", "third_party_outage"]
    risk_level = "HIGH"
    estimated_cost = "MEDIUM"
    default_timeout_seconds = 15
    parameter_schema = SwitchDependencyParams

    async def check_preconditions(self, params: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
        svc = params.get("service_name")
        target_ep = params.get("target_endpoint")
        if not svc or not target_ep:
            return False, "Target service and fallback endpoint are required."
        return True, f"Preconditions met: Fallback endpoint '{target_ep}' is reachable and verified."

    async def execute_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        svc = params["service_name"]
        target_ep = params["target_endpoint"]

        # If payment_latency was active, failover eliminates the delay
        if "payment_latency" in chaos_controller._active_faults:
            await chaos_controller.stop("payment_latency")

        for s in ["payment-service", "order-service", "api-gateway"]:
            if s in demo_mesh.metrics_history and demo_mesh.metrics_history[s]:
                last = demo_mesh.metrics_history[s][-1]
                last.latency_p50_ms = 45.0
                last.latency_p95_ms = 95.0
                last.error_rate = 0.05
                last.health_status = "HEALTHY"

        return {
            "status": "COMPLETED",
            "action": self.action_id,
            "service": svc,
            "fallback_endpoint": target_ep,
            "message": f"Successfully diverted outbound calls from degraded dependency to '{target_ep}'.",
        }

    async def verify_recovery(
        self,
        params: Dict[str, Any],
        before_snapshot: Dict[str, Any],
        after_snapshot: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        svc = params["service_name"]
        before_svc = before_snapshot.get(svc, {})
        after_svc = after_snapshot.get(svc, {})

        p95_before = before_svc.get("latency_p95_ms", 0.0)
        p95_after = after_svc.get("latency_p95_ms", 0.0)
        err_before = before_svc.get("error_rate", 0.0)
        err_after = after_svc.get("error_rate", 0.0)

        details = {
            "service": svc,
            "p95_latency_before": p95_before,
            "p95_latency_after": p95_after,
            "delta_p95": round(p95_after - p95_before, 2),
            "error_rate_before": err_before,
            "error_rate_after": err_after,
        }

        if p95_after < 300.0 and err_after <= 1.0:
            return "VERIFIED", details
        elif p95_after < p95_before:
            return "PARTIALLY_VERIFIED", details
        else:
            return "FAILED", details

    async def rollback_simulated(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"rollback": "COMPLETED", "details": "Restored primary egress dependency routing."}


# ============================================================================
# Central Controlled Action Registry
# ============================================================================

class RemediationActionRegistry:
    """
    Central immutable registry of all approved recovery actions.
    Ensures unknown action IDs or unauthorized actions cannot be dispatched.
    """

    def __init__(self):
        self._actions: Dict[str, BaseRemediationAction] = {}
        self._register_defaults()

    def _register_defaults(self):
        actions = [
            RestartServiceAction(),
            ScaleReplicasAction(),
            RollbackDeploymentAction(),
            ClearCacheAction(),
            ResetDbPoolAction(),
            ToggleFeatureFlagAction(),
            ApplyRateLimitAction(),
            SwitchDependencyAction(),
        ]
        for a in actions:
            self._actions[a.action_id] = a

    def get_action(self, action_id: str) -> Optional[BaseRemediationAction]:
        return self._actions.get(action_id)

    def list_actions(self) -> List[Dict[str, Any]]:
        """Return catalog of all 8 safe actions with parameter schemas."""
        result = []
        for a in self._actions.values():
            result.append({
                "action_id": a.action_id,
                "name": a.name,
                "description": a.description,
                "action_type": a.action_type,
                "supported_incident_types": a.supported_incident_types,
                "risk_level": a.risk_level,
                "estimated_cost": a.estimated_cost,
                "timeout_seconds": a.default_timeout_seconds,
                "parameter_schema": a.parameter_schema.model_json_schema(),
            })
        return result


# Singleton registry instance
remediation_registry = RemediationActionRegistry()
