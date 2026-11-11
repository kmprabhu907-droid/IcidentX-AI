"""
INCIDENTX AI - Demonstration Microservice Mesh & Observability Collector
Simulates an e-commerce distributed system with 7 nodes (API Gateway, Auth, Order, Payment,
Inventory, PostgreSQL, Redis) emitting OpenTelemetry-compliant traces, Prometheus-compatible
metrics, and structured correlated logs.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import math
import random
import time
from typing import Any, Deque, Dict, List, Optional
import uuid

from backend.app.core.logging import logger


class Span:
    """Represents a distributed trace span."""
    def __init__(
        self,
        span_id: str,
        trace_id: str,
        service_name: str,
        name: str,
        start_offset_ms: float,
        duration_ms: float,
        parent_span_id: Optional[str] = None,
        status: str = "OK",  # OK or ERROR
        status_code: int = 200,
        tags: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        self.span_id = span_id
        self.trace_id = trace_id
        self.service_name = service_name
        self.name = name
        self.parent_span_id = parent_span_id
        self.start_offset_ms = round(start_offset_ms, 2)
        self.duration_ms = round(duration_ms, 2)
        self.status = status
        self.status_code = status_code
        self.tags = tags or {}
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "service_name": self.service_name,
            "name": self.name,
            "parent_span_id": self.parent_span_id,
            "start_offset_ms": self.start_offset_ms,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "status_code": self.status_code,
            "tags": self.tags,
            "error_message": self.error_message,
        }


class Trace:
    """Represents an end-to-end distributed trace."""
    def __init__(
        self,
        trace_id: str,
        root_service: str,
        operation_name: str,
        start_time: datetime,
        duration_ms: float,
        status_code: int = 200,
        has_error: bool = False,
        data_source: str = "LIVE",
        spans: Optional[List[Span]] = None,
    ):
        self.trace_id = trace_id
        self.root_service = root_service
        self.operation_name = operation_name
        self.start_time = start_time
        self.duration_ms = round(duration_ms, 2)
        self.status_code = status_code
        self.has_error = has_error
        self.data_source = data_source
        self.spans: List[Span] = spans or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "root_service": self.root_service,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "duration_ms": self.duration_ms,
            "status_code": self.status_code,
            "has_error": self.has_error,
            "data_source": self.data_source,
            "span_count": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


class LogRecord:
    """Represents a structured log entry correlated with distributed tracing."""
    def __init__(
        self,
        timestamp: datetime,
        service_name: str,
        level: str,  # INFO, WARN, ERROR, DEBUG
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        data_source: str = "LIVE",
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = timestamp
        self.service_name = service_name
        self.level = level
        self.message = message
        self.trace_id = trace_id
        self.span_id = span_id
        self.context = context or {}
        self.data_source = data_source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "level": self.level,
            "message": self.message,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "context": self.context,
            "data_source": self.data_source,
        }


class ServiceMetricSnapshot:
    """
    1-second resolution point-in-time metrics for a microservice.
    Expanded in Phase 5 to deliver all 10 Golden Reliability Signals:
    1. CPU utilization (%)
    2. Memory utilization (%)
    3. Disk utilization (%)
    4. Network throughput (MB/s)
    5. Request latency (P50, P95, P99 ms)
    6. HTTP error rate (%)
    7. Database connection-pool utilization (%)
    8. Service availability (%)
    9. Dependency health score (%)
    10. Request throughput (RPS)
    """
    def __init__(
        self,
        timestamp: datetime,
        service_name: str,
        request_count: int,
        request_rate: float,
        error_count: int,
        error_rate: float,
        latency_p50_ms: float,
        latency_p95_ms: float,
        latency_p99_ms: float,
        cpu_utilization: float,
        memory_utilization: float,
        db_pool_utilization: float,
        health_status: str = "HEALTHY",
        data_source: str = "SIMULATED",
        # Phase 5 Ten-Signal Extensions
        service_id: Optional[str] = None,
        disk_utilization: float = 30.0,
        network_throughput_mbps: float = 10.0,
        availability_pct: float = 100.0,
        dependency_health: float = 100.0,
    ):
        self.timestamp = timestamp
        self.service_name = service_name
        self.service_id = service_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, service_name))
        self.request_count = request_count
        self.request_rate = round(request_rate, 2)
        self.error_count = error_count
        self.error_rate = round(error_rate, 2)
        self.latency_p50_ms = round(latency_p50_ms, 2)
        self.latency_p95_ms = round(latency_p95_ms, 2)
        self.latency_p99_ms = round(latency_p99_ms, 2)
        self.cpu_utilization = round(cpu_utilization, 2)
        self.memory_utilization = round(memory_utilization, 2)
        self.db_pool_utilization = round(db_pool_utilization, 2)
        self.disk_utilization = round(disk_utilization, 2)
        self.network_throughput_mbps = round(network_throughput_mbps, 2)
        self.availability_pct = round(availability_pct, 2)
        self.dependency_health = round(dependency_health, 2)
        self.health_status = health_status
        self.data_source = data_source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "service_id": self.service_id,
            "service_name": self.service_name,
            "request_count": self.request_count,
            "request_rate": self.request_rate,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "cpu_utilization": self.cpu_utilization,
            "memory_utilization": self.memory_utilization,
            "disk_utilization": self.disk_utilization,
            "network_throughput_mbps": self.network_throughput_mbps,
            "db_pool_utilization": self.db_pool_utilization,
            "availability_pct": self.availability_pct,
            "dependency_health": self.dependency_health,
            "health_status": self.health_status,
            "data_source": self.data_source,
        }


class DemoMesh:
    """
    Demonstration Microservice Mesh Simulator.
    Generates realistic real-time telemetry across 7 nodes:
    - api-gateway
    - auth-service
    - order-service
    - payment-service
    - inventory-service
    - postgres-db
    - redis-cache
    """

    SERVICE_ID_MAP = {
        "order-service": "e807c9f6-ea2b-426c-89bb-d63a08dca858",
        "inventory-db": "4f75f224-6132-4f44-8839-a97f74848738",
        "api-gateway": "488832cd-c3ca-487c-9609-73e1a5bbf1f8",
        "auth-service": "3e84246d-61e1-47ba-97ba-7bd08956898b",
        "payment-service": "6442e306-f7af-473f-a384-9962462db03c",
        "inventory-service": "9a5b88c4-c17c-4f72-869f-7a1fde0a3f22",
        "postgres-db": "823374bc-d4e1-4708-bd6d-d8eb63428914",
        "redis-cache": "8abc7410-272c-4057-adea-271255943eca",
    }

    SERVICE_DEFINITIONS = {
        "api-gateway": {
            "tier": "Tier-1",
            "type": "gateway",
            "language": "Go",
            "version": "v1.4.2",
            "base_rps": 24.0,
            "base_p50": 35.0,
            "base_cpu": 22.0,
            "base_mem": 42.0,
            "base_disk": 32.0,
            "base_net_mbps": 16.5,
        },
        "auth-service": {
            "tier": "Tier-1",
            "type": "service",
            "language": "Rust",
            "version": "v1.2.0",
            "base_rps": 18.0,
            "base_p50": 15.0,
            "base_cpu": 18.0,
            "base_mem": 35.0,
            "base_disk": 26.0,
            "base_net_mbps": 9.2,
        },
        "order-service": {
            "tier": "Tier-1",
            "type": "service",
            "language": "Python",
            "version": "v2.0.4",
            "base_rps": 12.0,
            "base_p50": 45.0,
            "base_cpu": 28.0,
            "base_mem": 52.0,
            "base_disk": 38.0,
            "base_net_mbps": 8.0,
        },
        "payment-service": {
            "tier": "Tier-1",
            "type": "service",
            "language": "Go",
            "version": "v1.8.1",
            "base_rps": 8.0,
            "base_p50": 55.0,
            "base_cpu": 20.0,
            "base_mem": 40.0,
            "base_disk": 28.0,
            "base_net_mbps": 5.5,
        },
        "inventory-service": {
            "tier": "Tier-2",
            "type": "service",
            "language": "TypeScript",
            "version": "v1.1.2",
            "base_rps": 15.0,
            "base_p50": 25.0,
            "base_cpu": 25.0,
            "base_mem": 48.0,
            "base_disk": 34.0,
            "base_net_mbps": 7.8,
        },
        "postgres-db": {
            "tier": "Tier-1",
            "type": "database",
            "language": "C",
            "version": "16.3",
            "base_rps": 40.0,
            "base_p50": 8.0,
            "base_cpu": 30.0,
            "base_mem": 65.0,
            "base_disk": 62.0,
            "base_net_mbps": 24.0,
        },
        "redis-cache": {
            "tier": "Tier-2",
            "type": "cache",
            "language": "C",
            "version": "7.2.4",
            "base_rps": 35.0,
            "base_p50": 2.0,
            "base_cpu": 12.0,
            "base_mem": 38.0,
            "base_disk": 16.0,
            "base_net_mbps": 14.0,
        },
    }

    DEPENDENCY_TOPOLOGY = [
        ("api-gateway", "auth-service", "HTTP", True),
        ("api-gateway", "order-service", "HTTP", True),
        ("api-gateway", "inventory-service", "HTTP", False),
        ("auth-service", "redis-cache", "TCP", True),
        ("auth-service", "postgres-db", "TCP", True),
        ("order-service", "payment-service", "HTTP", True),
        ("order-service", "inventory-service", "HTTP", True),
        ("order-service", "postgres-db", "TCP", True),
        ("payment-service", "postgres-db", "TCP", True),
        ("inventory-service", "postgres-db", "TCP", True),
        ("inventory-service", "redis-cache", "TCP", False),
    ]

    def __init__(self, history_seconds: int = 300):
        self.history_seconds = history_seconds
        # Ring buffers for time-series metrics per service (1 snapshot per second)
        self.metrics_history: Dict[str, Deque[ServiceMetricSnapshot]] = {
            s: deque(maxlen=history_seconds) for s in self.SERVICE_DEFINITIONS
        }
        # Ring buffer for recent distributed traces (up to 500)
        self.traces: Deque[Trace] = deque(maxlen=500)
        # Ring buffer for recent structured logs (up to 1000)
        self.logs: Deque[LogRecord] = deque(maxlen=1000)
        # Active fault overrides from Chaos Controller
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        # Running state
        self._running = False
        self._background_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._tick_count = 0

        # Pre-populate 30 seconds of healthy initial baseline
        self._seed_initial_history(30)

    def _seed_initial_history(self, seconds: int):
        now = datetime.now(timezone.utc)
        for i in range(seconds, 0, -1):
            t = now.fromtimestamp(now.timestamp() - i, tz=timezone.utc)
            for svc_name, defs in self.SERVICE_DEFINITIONS.items():
                jitter = math.sin(i * 0.1) * 2.0 + random.uniform(-1.0, 1.0)
                rps = max(1.0, defs["base_rps"] + jitter)
                err_rate = max(0.0, 0.05 + random.uniform(-0.02, 0.05))
                err_count = int(rps * (err_rate / 100.0))
                p50 = max(1.0, defs["base_p50"] + random.uniform(-2.0, 2.0))
                p95 = p50 * 2.2 + random.uniform(0.0, 5.0)
                p99 = p50 * 3.8 + random.uniform(0.0, 10.0)
                cpu = min(100.0, max(5.0, defs["base_cpu"] + jitter))
                mem = min(100.0, max(10.0, defs["base_mem"] + random.uniform(-1.0, 1.0)))
                db_pool = 15.0 + random.uniform(-2.0, 3.0) if "db" in svc_name or svc_name == "order-service" else 0.0
                disk = min(100.0, max(5.0, defs.get("base_disk", 30.0) + random.uniform(-0.2, 0.2)))
                net_mbps = max(0.1, round((defs.get("base_net_mbps", 10.0) * (rps / max(1.0, defs["base_rps"]))) + random.uniform(-0.2, 0.2), 2))
                availability = 100.0 - min(0.05, err_rate)
                dep_health = 100.0
                service_id = self.SERVICE_ID_MAP.get(svc_name, str(uuid.uuid5(uuid.NAMESPACE_DNS, svc_name)))

                snapshot = ServiceMetricSnapshot(
                    timestamp=t,
                    service_name=svc_name,
                    service_id=service_id,
                    request_count=int(rps),
                    request_rate=rps,
                    error_count=err_count,
                    error_rate=err_rate,
                    latency_p50_ms=p50,
                    latency_p95_ms=p95,
                    latency_p99_ms=p99,
                    cpu_utilization=cpu,
                    memory_utilization=mem,
                    db_pool_utilization=db_pool,
                    disk_utilization=disk,
                    network_throughput_mbps=net_mbps,
                    availability_pct=availability,
                    dependency_health=dep_health,
                    health_status="HEALTHY",
                    data_source="SIMULATED",
                )
                self.metrics_history[svc_name].append(snapshot)

    def set_fault(self, scenario_id: str, config: Dict[str, Any]):
        """Inject an active fault configured by Chaos Controller."""
        self.active_faults[scenario_id] = config
        logger.info(f"[DemoMesh] Injected fault scenario '{scenario_id}': {config}")

    def clear_fault(self, scenario_id: str):
        """Remove an active fault."""
        if scenario_id in self.active_faults:
            del self.active_faults[scenario_id]
            logger.info(f"[DemoMesh] Cleared fault scenario '{scenario_id}'")

    def clear_all_faults(self):
        """Clear all active chaos injections."""
        self.active_faults.clear()
        logger.info("[DemoMesh] All fault scenarios cleared. Returned to standard baseline.")

    def get_latest_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Return the latest metric snapshot for all services."""
        result = {}
        for svc_name, queue in self.metrics_history.items():
            if queue:
                result[svc_name] = queue[-1].to_dict()
            else:
                result[svc_name] = {}
        return result

    def get_service_history(self, service_name: str, seconds: int = 60) -> List[Dict[str, Any]]:
        """Return chronological history for a specific service."""
        queue = self.metrics_history.get(service_name)
        if not queue:
            return []
        items = list(queue)[-seconds:]
        return [item.to_dict() for item in items]

    def get_traces(
        self,
        limit: int = 50,
        service: Optional[str] = None,
        only_errors: bool = False,
        min_duration_ms: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Filter and return recent distributed traces."""
        traces = list(self.traces)
        filtered = []
        for t in reversed(traces):
            if service and t.root_service != service and not any(s.service_name == service for s in t.spans):
                continue
            if only_errors and not t.has_error:
                continue
            if min_duration_ms and t.duration_ms < min_duration_ms:
                continue
            filtered.append(t.to_dict())
            if len(filtered) >= limit:
                break
        return filtered

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific trace by ID."""
        for t in self.traces:
            if t.trace_id == trace_id:
                return t.to_dict()
        return None

    def get_logs(
        self,
        limit: int = 100,
        service: Optional[str] = None,
        level: Optional[str] = None,
        trace_id: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter and return recent structured logs."""
        logs = list(self.logs)
        filtered = []
        for log in reversed(logs):
            if service and log.service_name != service:
                continue
            if level and log.level.upper() != level.upper():
                continue
            if trace_id and log.trace_id != trace_id:
                continue
            if search and search.lower() not in log.message.lower():
                continue
            filtered.append(log.to_dict())
            if len(filtered) >= limit:
                break
        return filtered

    async def tick(self):
        """Execute one simulation cycle (1 second interval)."""
        async with self._lock:
            self._tick_count += 1
            now = datetime.now(timezone.utc)
            is_simulated = len(self.active_faults) > 0
            data_source = "SIMULATED" if is_simulated else "LIVE"

            # Check active fault parameters
            cpu_spike_target = None
            mem_leak_target = None
            payment_latency_ms = 0.0
            db_exhaustion = False
            redis_down = False
            http_500_cascade = False
            traffic_multiplier = 1.0
            instance_dead_target = None
            buggy_deployment = False

            for scenario_id, cfg in self.active_faults.items():
                if scenario_id == "cpu_spike":
                    cpu_spike_target = cfg.get("target_service", "order-service")
                elif scenario_id == "memory_leak":
                    mem_leak_target = cfg.get("target_service", "order-service")
                elif scenario_id == "payment_latency":
                    payment_latency_ms = float(cfg.get("latency_ms", 2500.0))
                elif scenario_id == "db_pool_exhaustion":
                    db_exhaustion = True
                elif scenario_id == "redis_down":
                    redis_down = True
                elif scenario_id == "http_500_cascade":
                    http_500_cascade = True
                elif scenario_id == "traffic_surge":
                    traffic_multiplier = float(cfg.get("multiplier", 5.0))
                elif scenario_id == "instance_termination":
                    instance_dead_target = cfg.get("target_service", "inventory-service")
                elif scenario_id == "deployment_regression":
                    buggy_deployment = True

            # Generate synthetic distributed traces & logs for this tick
            flow_types = ["checkout", "login", "browse"]
            traces_to_generate = int(random.randint(2, 5) * (traffic_multiplier if traffic_multiplier <= 3.0 else 3.0))

            for _ in range(traces_to_generate):
                flow = random.choice(flow_types)
                await self._simulate_flow(
                    flow=flow,
                    now=now,
                    data_source=data_source,
                    payment_latency_ms=payment_latency_ms,
                    db_exhaustion=db_exhaustion,
                    redis_down=redis_down,
                    http_500_cascade=http_500_cascade,
                    instance_dead_target=instance_dead_target,
                    buggy_deployment=buggy_deployment,
                )

            # Compute metric snapshots for all 7 services
            for svc_name, defs in self.SERVICE_DEFINITIONS.items():
                prev = self.metrics_history[svc_name][-1] if self.metrics_history[svc_name] else None

                # Calculate base metrics
                rps = (defs["base_rps"] * traffic_multiplier) + random.uniform(-1.5, 1.5)
                rps = max(0.5, rps)
                p50 = defs["base_p50"] + random.uniform(-2.0, 2.0)
                p95 = p50 * 2.2 + random.uniform(1.0, 6.0)
                p99 = p50 * 3.8 + random.uniform(2.0, 12.0)
                cpu = defs["base_cpu"] + random.uniform(-2.0, 2.0)
                mem = defs["base_mem"] + random.uniform(-0.5, 0.5)
                db_pool = 18.0 + random.uniform(-3.0, 3.0) if "db" in svc_name or svc_name in ["order-service", "payment-service"] else 0.0
                error_rate = 0.1 + random.uniform(0.0, 0.15)
                health = "HEALTHY"

                # Apply fault effects
                if cpu_spike_target == svc_name:
                    cpu = min(100.0, 95.0 + random.uniform(0.0, 4.5))
                    p50 *= 3.0
                    p95 *= 4.5
                    p99 *= 6.0
                    health = "DEGRADED"

                if mem_leak_target == svc_name:
                    leak_rate = float(self.active_faults.get("memory_leak", {}).get("leak_rate", 2.0))
                    prev_mem = prev.memory_utilization if prev else 50.0
                    mem = min(98.5, prev_mem + leak_rate + random.uniform(0.0, 1.0))
                    if mem > 85.0:
                        health = "DEGRADED" if mem < 92.0 else "CRITICAL"
                        p95 += (mem - 80.0) * 15.0
                        p99 += (mem - 80.0) * 35.0

                if payment_latency_ms > 0:
                    if svc_name == "payment-service":
                        p50 += payment_latency_ms
                        p95 += payment_latency_ms + 400.0
                        p99 += payment_latency_ms + 800.0
                        health = "CRITICAL"
                    elif svc_name == "order-service":
                        p50 += 800.0
                        p95 += 2100.0
                        p99 += 2400.0
                        error_rate = min(100.0, error_rate + 65.0)
                        health = "CRITICAL"
                    elif svc_name == "api-gateway":
                        p95 += 1800.0
                        error_rate = min(100.0, error_rate + 45.0)
                        health = "DEGRADED"

                if db_exhaustion:
                    if svc_name == "postgres-db":
                        db_pool = 100.0
                        cpu = min(100.0, cpu + 55.0)
                        health = "CRITICAL"
                    elif svc_name in ["order-service", "payment-service", "inventory-service"]:
                        db_pool = 100.0
                        error_rate = min(100.0, error_rate + 82.0)
                        health = "CRITICAL"
                    elif svc_name == "api-gateway":
                        error_rate = min(100.0, error_rate + 70.0)
                        health = "CRITICAL"

                if redis_down:
                    if svc_name == "redis-cache":
                        health = "CRITICAL"
                        error_rate = 100.0
                        rps = 0.0
                    elif svc_name == "auth-service":
                        health = "DEGRADED"
                        error_rate = min(100.0, error_rate + 35.0)
                        p95 += 300.0

                if http_500_cascade:
                    if svc_name == "order-service":
                        error_rate = min(100.0, error_rate + 75.0)
                        health = "CRITICAL"
                    elif svc_name == "api-gateway":
                        error_rate = min(100.0, error_rate + 55.0)
                        health = "DEGRADED"

                if traffic_multiplier > 1.5:
                    cpu = min(98.0, cpu * min(2.5, traffic_multiplier * 0.7))
                    p95 *= min(2.8, traffic_multiplier * 0.8)
                    p99 *= min(3.5, traffic_multiplier)
                    if traffic_multiplier >= 4.0:
                        error_rate = min(100.0, error_rate + 12.0)
                        health = "DEGRADED"

                if instance_dead_target == svc_name:
                    health = "CRITICAL"
                    error_rate = 100.0
                    rps = 0.0
                    cpu = 0.0
                    mem = 0.0

                if buggy_deployment and svc_name == "order-service":
                    error_rate = min(100.0, error_rate + 58.0)
                    health = "CRITICAL"

                # Keep bounds valid
                cpu = min(100.0, max(0.0, cpu))
                mem = min(100.0, max(0.0, mem))
                db_pool = min(100.0, max(0.0, db_pool))
                error_rate = min(100.0, max(0.0, error_rate))
                err_count = int(rps * (error_rate / 100.0))

                # Phase 5 Golden Signals calculation
                disk = defs.get("base_disk", 30.0) + random.uniform(-0.5, 0.5)
                if db_exhaustion and svc_name == "postgres-db":
                    disk = min(98.0, disk + 28.0)
                disk = min(100.0, max(0.0, disk))

                net_mbps = max(0.0, round((defs.get("base_net_mbps", 10.0) * (rps / max(1.0, defs["base_rps"]))) + random.uniform(-0.5, 0.5), 2))

                if instance_dead_target == svc_name or (rps == 0.0 and svc_name != "postgres-db"):
                    availability = 0.0
                elif health == "HEALTHY":
                    availability = round(max(0.0, min(100.0, 100.0 - min(0.1, error_rate))), 2)
                elif health == "DEGRADED":
                    availability = round(max(0.0, min(100.0, 100.0 - (error_rate * 0.7))), 2)
                else:
                    availability = round(max(0.0, min(100.0, 100.0 - error_rate)), 2)

                # Dependency health calculation
                if payment_latency_ms > 0:
                    if svc_name == "order-service":
                        dep_health = 25.0
                    elif svc_name == "api-gateway":
                        dep_health = 45.0
                    else:
                        dep_health = 100.0
                elif db_exhaustion and svc_name in ["order-service", "payment-service", "inventory-service"]:
                    dep_health = 15.0
                elif redis_down and svc_name in ["auth-service", "inventory-service"]:
                    dep_health = 40.0
                else:
                    dep_health = 100.0 if health == "HEALTHY" else (70.0 if health == "DEGRADED" else 40.0)

                service_id = self.SERVICE_ID_MAP.get(svc_name, str(uuid.uuid5(uuid.NAMESPACE_DNS, svc_name)))

                snapshot = ServiceMetricSnapshot(
                    timestamp=now,
                    service_name=svc_name,
                    service_id=service_id,
                    request_count=int(rps),
                    request_rate=rps,
                    error_count=err_count,
                    error_rate=error_rate,
                    latency_p50_ms=p50,
                    latency_p95_ms=p95,
                    latency_p99_ms=p99,
                    cpu_utilization=cpu,
                    memory_utilization=mem,
                    db_pool_utilization=db_pool,
                    disk_utilization=disk,
                    network_throughput_mbps=net_mbps,
                    availability_pct=availability,
                    dependency_health=dep_health,
                    health_status=health,
                    data_source=data_source,
                )
                self.metrics_history[svc_name].append(snapshot)

    async def _simulate_flow(
        self,
        flow: str,
        now: datetime,
        data_source: str,
        payment_latency_ms: float,
        db_exhaustion: bool,
        redis_down: bool,
        http_500_cascade: bool,
        instance_dead_target: Optional[str],
        buggy_deployment: bool,
    ):
        """Simulate a single distributed transaction across service boundaries."""
        trace_id = uuid.uuid4().hex
        spans: List[Span] = []
        offset = 0.0

        if flow == "checkout":
            # API Gateway -> Auth Service -> Order Service (Inventory, Payment, DB)
            root_span_id = uuid.uuid4().hex[:16]
            has_error = False
            root_status = 200

            # 1. API Gateway root span
            gw_span = Span(
                span_id=root_span_id,
                trace_id=trace_id,
                service_name="api-gateway",
                name="POST /api/v1/checkout",
                start_offset_ms=0.0,
                duration_ms=45.0,
                parent_span_id=None,
            )
            spans.append(gw_span)

            # 2. Auth Service check
            auth_span_id = uuid.uuid4().hex[:16]
            auth_duration = 12.0
            auth_status = "OK"
            auth_code = 200

            if redis_down:
                auth_status = "ERROR"
                auth_code = 500
                has_error = True
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="auth-service",
                    level="ERROR",
                    message="RedisConnectionError: Connection refused (redis-cache:6379)",
                    trace_id=trace_id,
                    span_id=auth_span_id,
                    data_source=data_source,
                ))

            spans.append(Span(
                span_id=auth_span_id,
                trace_id=trace_id,
                service_name="auth-service",
                name="POST /auth/verify-token",
                start_offset_ms=2.0,
                duration_ms=auth_duration,
                parent_span_id=root_span_id,
                status=auth_status,
                status_code=auth_code,
            ))

            # 3. Order Service
            order_span_id = uuid.uuid4().hex[:16]
            order_duration = 55.0
            order_status = "OK"
            order_code = 200
            order_error_msg = None

            if buggy_deployment:
                order_status = "ERROR"
                order_code = 500
                order_error_msg = "NullPointerException: CartItem.currency cannot be null in compute_totals"
                has_error = True
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="order-service",
                    level="ERROR",
                    message="NullPointerException: CartItem.currency is null at OrderEngine.java:142",
                    trace_id=trace_id,
                    span_id=order_span_id,
                    data_source=data_source,
                ))
            elif http_500_cascade:
                order_status = "ERROR"
                order_code = 500
                order_error_msg = "InternalServerError: Transaction rollback forced by upstream error"
                has_error = True
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="order-service",
                    level="ERROR",
                    message="HTTP 500: Failed to process order payload - unhandled exception",
                    trace_id=trace_id,
                    span_id=order_span_id,
                    data_source=data_source,
                ))
            elif db_exhaustion:
                order_status = "ERROR"
                order_code = 503
                order_error_msg = "ConnectionPoolTimeoutException: pool exhausted after 3000ms"
                has_error = True
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="order-service",
                    level="ERROR",
                    message="ConnectionPoolTimeoutException: unable to acquire connection from postgres-db pool (max: 50)",
                    trace_id=trace_id,
                    span_id=order_span_id,
                    data_source=data_source,
                ))
            elif payment_latency_ms > 0:
                # Upstream payment timeout
                order_status = "ERROR"
                order_code = 504
                order_error_msg = f"PaymentGatewayTimeoutException: upstream payment timeout after {payment_latency_ms}ms"
                has_error = True
                order_duration = min(2000.0, payment_latency_ms)
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="order-service",
                    level="ERROR",
                    message=f"PaymentTimeout: payment-service timed out after {order_duration:.0f}ms (threshold 2000ms)",
                    trace_id=trace_id,
                    span_id=order_span_id,
                    data_source=data_source,
                ))

            # 4. Inventory check span
            inv_span_id = uuid.uuid4().hex[:16]
            inv_status = "OK"
            inv_code = 200
            inv_error_msg = None
            if instance_dead_target == "inventory-service":
                inv_status = "ERROR"
                inv_code = 503
                inv_error_msg = "ConnectionRefused: inventory-service replica unready"
                has_error = True
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="inventory-service",
                    level="ERROR",
                    message="PodCrashLoopBackOff: inventory-service termination signal SIGSEGV",
                    trace_id=trace_id,
                    span_id=inv_span_id,
                    data_source=data_source,
                ))

            spans.append(Span(
                span_id=inv_span_id,
                trace_id=trace_id,
                service_name="inventory-service",
                name="POST /stock/reserve",
                start_offset_ms=16.0,
                duration_ms=18.0,
                parent_span_id=order_span_id,
                status=inv_status,
                status_code=inv_code,
                error_message=inv_error_msg,
            ))

            # 5. Payment Service span
            pay_span_id = uuid.uuid4().hex[:16]
            pay_duration = 38.0 + payment_latency_ms
            pay_status = "ERROR" if (payment_latency_ms > 2000.0 or db_exhaustion) else "OK"
            pay_code = 504 if payment_latency_ms > 2000.0 else (503 if db_exhaustion else 200)
            pay_error = "Timeout waiting for PSP response" if payment_latency_ms > 2000.0 else None

            spans.append(Span(
                span_id=pay_span_id,
                trace_id=trace_id,
                service_name="payment-service",
                name="POST /v1/charge",
                start_offset_ms=36.0,
                duration_ms=pay_duration,
                parent_span_id=order_span_id,
                status=pay_status,
                status_code=pay_code,
                error_message=pay_error,
            ))

            # Order span duration adjustment
            order_span = Span(
                span_id=order_span_id,
                trace_id=trace_id,
                service_name="order-service",
                name="POST /orders/create",
                start_offset_ms=15.0,
                duration_ms=order_duration + pay_duration,
                parent_span_id=root_span_id,
                status=order_status,
                status_code=order_code,
                error_message=order_error_msg,
            )
            spans.append(order_span)

            total_trace_duration = 15.0 + order_span.duration_ms + 10.0
            gw_span.duration_ms = total_trace_duration
            if has_error:
                gw_span.status = "ERROR"
                gw_span.status_code = 502 if order_code in [500, 503, 504] else order_code
                root_status = gw_span.status_code

            trace = Trace(
                trace_id=trace_id,
                root_service="api-gateway",
                operation_name="POST /api/v1/checkout",
                start_time=now,
                duration_ms=total_trace_duration,
                status_code=root_status,
                has_error=has_error,
                data_source=data_source,
                spans=spans,
            )
            self.traces.append(trace)

            # Normal or warning logs
            if not has_error:
                self.logs.append(LogRecord(
                    timestamp=now,
                    service_name="order-service",
                    level="INFO",
                    message="Order created successfully. Payment captured.",
                    trace_id=trace_id,
                    span_id=order_span_id,
                    data_source=data_source,
                ))

        elif flow == "login":
            root_span_id = uuid.uuid4().hex[:16]
            auth_span_id = uuid.uuid4().hex[:16]
            cache_span_id = uuid.uuid4().hex[:16]

            has_error = redis_down
            status_code = 500 if redis_down else 200

            spans.append(Span(
                span_id=root_span_id,
                trace_id=trace_id,
                service_name="api-gateway",
                name="POST /api/v1/login",
                start_offset_ms=0.0,
                duration_ms=28.0,
                status="ERROR" if has_error else "OK",
                status_code=status_code,
            ))
            spans.append(Span(
                span_id=auth_span_id,
                trace_id=trace_id,
                service_name="auth-service",
                name="POST /auth/authenticate",
                start_offset_ms=2.0,
                duration_ms=22.0,
                parent_span_id=root_span_id,
                status="ERROR" if has_error else "OK",
                status_code=status_code,
            ))
            spans.append(Span(
                span_id=cache_span_id,
                trace_id=trace_id,
                service_name="redis-cache",
                name="SETEX session:user",
                start_offset_ms=6.0,
                duration_ms=3.0,
                parent_span_id=auth_span_id,
                status="ERROR" if redis_down else "OK",
                status_code=500 if redis_down else 200,
            ))

            self.traces.append(Trace(
                trace_id=trace_id,
                root_service="api-gateway",
                operation_name="POST /api/v1/login",
                start_time=now,
                duration_ms=28.0,
                status_code=status_code,
                has_error=has_error,
                data_source=data_source,
                spans=spans,
            ))

        else:  # browse
            root_span_id = uuid.uuid4().hex[:16]
            inv_span_id = uuid.uuid4().hex[:16]
            has_error = instance_dead_target == "inventory-service"
            status_code = 503 if has_error else 200

            spans.append(Span(
                span_id=root_span_id,
                trace_id=trace_id,
                service_name="api-gateway",
                name="GET /api/v1/products",
                start_offset_ms=0.0,
                duration_ms=18.0,
                status="ERROR" if has_error else "OK",
                status_code=status_code,
            ))
            spans.append(Span(
                span_id=inv_span_id,
                trace_id=trace_id,
                service_name="inventory-service",
                name="GET /catalog/items",
                start_offset_ms=2.0,
                duration_ms=14.0,
                parent_span_id=root_span_id,
                status="ERROR" if has_error else "OK",
                status_code=status_code,
            ))

            self.traces.append(Trace(
                trace_id=trace_id,
                root_service="api-gateway",
                operation_name="GET /api/v1/products",
                start_time=now,
                duration_ms=18.0,
                status_code=status_code,
                has_error=has_error,
                data_source=data_source,
                spans=spans,
            ))

    async def start(self):
        """Start the background telemetry generation loop."""
        if self._running:
            return
        self._running = True

        async def _loop():
            logger.info("[DemoMesh] Telemetry generator background loop started.")
            while self._running:
                try:
                    await self.tick()
                except Exception as e:
                    logger.error(f"[DemoMesh] Error in simulation tick: {e}", exc_info=True)
                await asyncio.sleep(1.0)
            logger.info("[DemoMesh] Telemetry generator loop stopped.")

        self._background_task = asyncio.create_task(_loop())

    async def stop(self):
        """Stop background telemetry generation."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None


# Singleton instance across application
demo_mesh = DemoMesh()
