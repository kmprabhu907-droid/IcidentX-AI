"""
INCIDENTX AI - Chaos Controller & Failure Injection Lab
Provides controlled, parameterized fault injection across 9 production failure scenarios.
All synthetic telemetry and events are strictly tagged with data_source='SIMULATED'.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from backend.app.core.logging import logger
from backend.app.services.observability.demo_mesh import demo_mesh


class ChaosScenarioMetadata:
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        target_service: str,
        category: str,
        default_duration_seconds: int,
        impact_summary: str,
        severity_potential: str,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.target_service = target_service
        self.category = category
        self.default_duration_seconds = default_duration_seconds
        self.impact_summary = impact_summary
        self.severity_potential = severity_potential

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_service": self.target_service,
            "category": self.category,
            "default_duration_seconds": self.default_duration_seconds,
            "impact_summary": self.impact_summary,
            "severity_potential": self.severity_potential,
        }


class ActiveFault:
    def __init__(
        self,
        fault_id: str,
        scenario_id: str,
        target_service: str,
        duration_seconds: int,
        parameters: Dict[str, Any],
        started_at: datetime,
    ):
        self.fault_id = fault_id
        self.scenario_id = scenario_id
        self.target_service = target_service
        self.duration_seconds = duration_seconds
        self.parameters = parameters
        self.started_at = started_at
        self.stop_task: Optional[asyncio.Task] = None

    def to_dict(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.started_at).total_seconds()
        remaining = max(0.0, self.duration_seconds - elapsed)
        return {
            "fault_id": self.fault_id,
            "scenario_id": self.scenario_id,
            "target_service": self.target_service,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(elapsed, 1),
            "remaining_seconds": round(remaining, 1),
            "parameters": self.parameters,
            "started_at": self.started_at.isoformat(),
            "data_source": "SIMULATED",
        }


class ChaosController:
    """
    Controller for the Failure Injection Lab.
    Manages lifecycle of active faults and hooks directly into the DemoMesh.
    """

    SCENARIOS = {
        "payment_latency": ChaosScenarioMetadata(
            id="payment_latency",
            name="Payment Gateway Upstream Latency",
            description="Injects 2500ms artificial delay into payment gateway transactions, causing upstream client timeouts and order failures.",
            target_service="payment-service",
            category="Network / Latency",
            default_duration_seconds=60,
            impact_summary="Payment P95 spikes to ~2.9s. Order service experiences 504 Gateway Timeouts.",
            severity_potential="SEV-2",
        ),
        "db_pool_exhaustion": ChaosScenarioMetadata(
            id="db_pool_exhaustion",
            name="Database Connection Pool Exhaustion",
            description="Exhausts 100% of PostgreSQL connection slots, preventing worker threads from acquiring pooled connections.",
            target_service="postgres-db",
            category="Infrastructure / Database",
            default_duration_seconds=60,
            impact_summary="Postgres pool hits 100%. Order and payment services throw ConnectionPoolTimeoutException.",
            severity_potential="SEV-1",
        ),
        "cpu_spike": ChaosScenarioMetadata(
            id="cpu_spike",
            name="CPU Starvation & Core Saturation",
            description="Spikes CPU utilization to 96%+ on target service, inducing thread starvation and request queuing.",
            target_service="order-service",
            category="Compute / Resource",
            default_duration_seconds=60,
            impact_summary="Order service CPU pinned at ~98%. Latency quadruples; worker queues back up.",
            severity_potential="SEV-3",
        ),
        "memory_leak": ChaosScenarioMetadata(
            id="memory_leak",
            name="Heap Memory Leak & GC Thrashing",
            description="Gradually inflates resident heap memory without freeing, triggering GC pauses and tail latency inflation.",
            target_service="order-service",
            category="Memory / Resource",
            default_duration_seconds=90,
            impact_summary="Memory climbs past 90%. P99 latency degrades rapidly under stop-the-world GC.",
            severity_potential="SEV-2",
        ),
        "redis_down": ChaosScenarioMetadata(
            id="redis_down",
            name="Redis Cache Outage & Refusal",
            description="Simulates unexpected Redis node failure (connection refused), forcing cache misses and session lookup errors.",
            target_service="redis-cache",
            category="Infrastructure / Cache",
            default_duration_seconds=60,
            impact_summary="Auth service fails token verification via cache. 100% error rate on Redis node.",
            severity_potential="SEV-3",
        ),
        "http_500_cascade": ChaosScenarioMetadata(
            id="http_500_cascade",
            name="HTTP 500 Unhandled Exception Cascade",
            description="Triggers uncaught runtime exceptions in business logic handlers, bubbling up 500 errors to callers.",
            target_service="order-service",
            category="Application / Software",
            default_duration_seconds=60,
            impact_summary="Order service error rate jumps to ~75%. API Gateway returns 502 Bad Gateway to clients.",
            severity_potential="SEV-1",
        ),
        "traffic_surge": ChaosScenarioMetadata(
            id="traffic_surge",
            name="Ingress Traffic Surge (5x Black Friday Spike)",
            description="Injects a massive 5x traffic surge on the API Gateway, stressing all downstream services simultaneously.",
            target_service="api-gateway",
            category="Traffic / Load",
            default_duration_seconds=60,
            impact_summary="Overall throughput jumps to 120+ req/s. CPU utilization doubles across the cluster.",
            severity_potential="SEV-2",
        ),
        "instance_termination": ChaosScenarioMetadata(
            id="instance_termination",
            name="Sudden Pod Crash / Node Failure",
            description="Simulates immediate crash of all healthy service replicas (SIGSEGV/OOMKill), returning 503.",
            target_service="inventory-service",
            category="Resilience / Infrastructure",
            default_duration_seconds=60,
            impact_summary="Target service returns 0 RPS with 100% error rate. Checkout flow fails to reserve inventory.",
            severity_potential="SEV-2",
        ),
        "deployment_regression": ChaosScenarioMetadata(
            id="deployment_regression",
            name="Faulty Release Regression (v2.1.0)",
            description="Deploys a buggy revision introducing NullPointerExceptions on specific cart calculation paths.",
            target_service="order-service",
            category="Deployment / Software",
            default_duration_seconds=60,
            impact_summary="Checkout operations fail with NullPointerException. Immediate rollback required.",
            severity_potential="SEV-2",
        ),
    }

    def __init__(self):
        self._active_faults: Dict[str, ActiveFault] = {}

    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.SCENARIOS.values()]

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        s = self.SCENARIOS.get(scenario_id)
        return s.to_dict() if s else None

    async def inject(
        self,
        scenario_id: str,
        target_service: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Inject a failure scenario into the running system.
        """
        scenario = self.SCENARIOS.get(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown chaos scenario: {scenario_id}")

        target = target_service or scenario.target_service
        duration = duration_seconds or scenario.default_duration_seconds
        params = parameters or {}

        # If already running, cancel the prior auto-stop timer
        if scenario_id in self._active_faults:
            existing = self._active_faults[scenario_id]
            if existing.stop_task and not existing.stop_task.done():
                existing.stop_task.cancel()

        fault_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Merge configs for DemoMesh
        config = {
            "target_service": target,
            "duration": duration,
            "data_source": "SIMULATED",
            **params,
        }

        # Update DemoMesh
        demo_mesh.set_fault(scenario_id, config)

        fault = ActiveFault(
            fault_id=fault_id,
            scenario_id=scenario_id,
            target_service=target,
            duration_seconds=duration,
            parameters=config,
            started_at=started_at,
        )

        # Schedule automatic stop when duration expires
        async def _auto_stop():
            try:
                await asyncio.sleep(duration)
                await self.stop(scenario_id)
                logger.info(f"[ChaosController] Auto-stopped scenario '{scenario_id}' after {duration}s")
            except asyncio.CancelledError:
                pass

        fault.stop_task = asyncio.create_task(_auto_stop())
        self._active_faults[scenario_id] = fault

        logger.info(f"[ChaosController] Injected chaos '{scenario_id}' targeting '{target}' for {duration}s")
        return fault.to_dict()

    async def stop(self, scenario_id: str) -> bool:
        """Stop a specific active fault scenario."""
        if scenario_id in self._active_faults:
            fault = self._active_faults.pop(scenario_id)
            if fault.stop_task and not fault.stop_task.done():
                fault.stop_task.cancel()
            demo_mesh.clear_fault(scenario_id)
            logger.info(f"[ChaosController] Stopped scenario '{scenario_id}'")
            return True
        return False

    async def stop_all(self) -> int:
        """Immediately stop all active chaos scenarios."""
        count = len(self._active_faults)
        for fault in list(self._active_faults.values()):
            if fault.stop_task and not fault.stop_task.done():
                fault.stop_task.cancel()
        self._active_faults.clear()
        demo_mesh.clear_all_faults()
        logger.info(f"[ChaosController] Emergency stopped all {count} active chaos scenarios.")
        return count

    def get_status(self) -> Dict[str, Any]:
        """Return status of all active fault injections."""
        active_list = [f.to_dict() for f in self._active_faults.values()]
        return {
            "is_active": len(active_list) > 0,
            "active_fault_count": len(active_list),
            "data_source": "SIMULATED" if active_list else "LIVE",
            "active_faults": active_list,
        }


# Singleton instance
chaos_controller = ChaosController()
