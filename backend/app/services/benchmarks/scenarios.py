"""
INCIDENTX AI - Realistic Infrastructure Incident Benchmark Scenarios (Stage 7.3)
Defines 15 production-grade infrastructure failure scenarios with ground-truth root causes,
telemetry signatures, log anomalies, expected remediation actions, and recovery verification criteria.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScenarioInfrastructureCondition(BaseModel):
    service_name: str
    baseline_cpu_percent: float
    baseline_memory_mb: float
    baseline_latency_ms: float
    baseline_error_rate: float
    active_instances: int
    dependencies: List[str] = Field(default_factory=list)


class ScenarioMetricEvidence(BaseModel):
    metric_name: str
    target_service: str
    observed_value: float
    threshold_value: float
    unit: str
    anomaly_type: str  # HIGH_UTILIZATION, SPIKE, LATENCY_BREACH, DROP, RESOURCE_CREEP
    is_primary_symptom: bool = False


class ScenarioLogEvidence(BaseModel):
    service_name: str
    level: str  # WARN, ERROR, FATAL
    message_pattern: str
    occurrences_per_min: int
    correlates_to_root_cause: bool = True


class ScenarioTimelineItem(BaseModel):
    offset_seconds: int
    event_type: str
    source_service: str
    description: str
    severity: str


class ScenarioRootCauseHypothesis(BaseModel):
    hypothesis_id: str
    title: str
    category: str
    description: str
    is_ground_truth: bool
    expected_confidence_min: float
    expected_confidence_max: float
    supporting_evidence_keys: List[str]
    contradicting_evidence_keys: List[str] = Field(default_factory=list)


class ScenarioRemediationRequirement(BaseModel):
    recommended_action: str
    target_service: str
    parameters: Dict[str, Any]
    requires_human_approval: bool
    risk_score: float
    alternative_actions: List[str] = Field(default_factory=list)


class ScenarioVerificationCondition(BaseModel):
    target_service: str
    metric_to_check: str
    expected_threshold: float
    operator: str  # LT, LTE, GT, GTE, EQ
    stabilization_window_seconds: int


class IncidentBenchmarkScenario(BaseModel):
    scenario_id: str
    name: str
    category: str
    severity: str
    target_service: str
    affected_services: List[str]
    description: str
    initial_conditions: List[ScenarioInfrastructureCondition]
    metric_evidence: List[ScenarioMetricEvidence]
    log_evidence: List[ScenarioLogEvidence]
    timeline: List[ScenarioTimelineItem]
    hypotheses: List[ScenarioRootCauseHypothesis]
    ground_truth_root_cause: str
    remediation: ScenarioRemediationRequirement
    verification: ScenarioVerificationCondition


# ==============================================================================
# The 15 Realistic Infrastructure Benchmark Scenarios
# ==============================================================================

BENCHMARK_SCENARIOS_LIBRARY: Dict[str, IncidentBenchmarkScenario] = {
    # --------------------------------------------------------------------------
    # 1. CPU Exhaustion
    # --------------------------------------------------------------------------
    "cpu_exhaustion": IncidentBenchmarkScenario(
        scenario_id="cpu_exhaustion",
        name="Payment Service CPU Saturation & Thread Starvation",
        category="COMPUTE_EXHAUSTION",
        severity="SEV-1",
        target_service="payment-service",
        affected_services=["payment-service", "order-service", "api-gateway"],
        description="Runaway cryptographic signature recalculations saturate CPU to 99%, starving worker threads.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="payment-service",
                baseline_cpu_percent=18.5,
                baseline_memory_mb=512.0,
                baseline_latency_ms=45.0,
                baseline_error_rate=0.001,
                active_instances=2,
                dependencies=["postgres", "redis"],
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="cpu_utilization",
                target_service="payment-service",
                observed_value=99.2,
                threshold_value=85.0,
                unit="percent",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="p99_latency_ms",
                target_service="payment-service",
                observed_value=2450.0,
                threshold_value=250.0,
                unit="ms",
                anomaly_type="LATENCY_BREACH",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="payment-service",
                level="ERROR",
                message_pattern="ThreadPoolExecutor starved: queue capacity exceeded 5000 tasks",
                occurrences_per_min=140,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="WORKLOAD_SURGE", source_service="api-gateway", description="Batch refund processing initiated", severity="INFO"),
            ScenarioTimelineItem(offset_seconds=25, event_type="RESOURCE_SPIKE", source_service="payment-service", description="CPU utilization crossed 90%", severity="WARNING"),
            ScenarioTimelineItem(offset_seconds=45, event_type="LATENCY_BREACH", source_service="payment-service", description="P99 response time exceeded 2000ms", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_cpu_starvation",
                title="Cryptographic Thread Starvation & Compute Exhaustion",
                category="COMPUTE",
                description="CPU saturated by unoptimized crypto loops starving request handling threads",
                is_ground_truth=True,
                expected_confidence_min=0.80,
                expected_confidence_max=0.98,
                supporting_evidence_keys=["cpu_utilization", "p99_latency_ms"],
            ),
            ScenarioRootCauseHypothesis(
                hypothesis_id="h2_db_lock",
                title="Database Deadlock Contention",
                category="DATABASE",
                description="Payment service blocked on database row locks",
                is_ground_truth=False,
                expected_confidence_min=0.10,
                expected_confidence_max=0.35,
                supporting_evidence_keys=["p99_latency_ms"],
                contradicting_evidence_keys=["postgres_active_connections_normal"],
            ),
        ],
        ground_truth_root_cause="Cryptographic Thread Starvation & Compute Exhaustion",
        remediation=ScenarioRemediationRequirement(
            recommended_action="scale_service",
            target_service="payment-service",
            parameters={"replicas": 4, "cpu_limit": "2000m"},
            requires_human_approval=False,
            risk_score=0.25,
            alternative_actions=["restart_pod", "rate_limit_caller"],
        ),
        verification=ScenarioVerificationCondition(
            target_service="payment-service",
            metric_to_check="cpu_utilization",
            expected_threshold=65.0,
            operator="LTE",
            stabilization_window_seconds=15,
        ),
    ),

    # --------------------------------------------------------------------------
    # 2. Memory Leak
    # --------------------------------------------------------------------------
    "memory_leak": IncidentBenchmarkScenario(
        scenario_id="memory_leak",
        name="Order Service Unbounded Heap Creep & OOM Risk",
        category="MEMORY_LEAK",
        severity="SEV-2",
        target_service="order-service",
        affected_services=["order-service", "inventory-service"],
        description="Unbounded event listener registration in Order service causes steady 15MB/min heap creep.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="order-service",
                baseline_cpu_percent=12.0,
                baseline_memory_mb=420.0,
                baseline_latency_ms=35.0,
                baseline_error_rate=0.000,
                active_instances=3,
                dependencies=["inventory-service", "postgres"],
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="memory_mb",
                target_service="order-service",
                observed_value=1950.0,
                threshold_value=1500.0,
                unit="MB",
                anomaly_type="RESOURCE_CREEP",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="gc_pause_time_ms",
                target_service="order-service",
                observed_value=850.0,
                threshold_value=100.0,
                unit="ms",
                anomaly_type="SPIKE",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="order-service",
                level="WARN",
                message_pattern="JVM GarbageCollection Overhead: full GC reclaiming < 2% heap",
                occurrences_per_min=45,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="CREEP_START", source_service="order-service", description="Heap memory began monotonic ascent", severity="INFO"),
            ScenarioTimelineItem(offset_seconds=120, event_type="GC_THRASH", source_service="order-service", description="Stop-the-world GC pauses reached 850ms", severity="WARNING"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_heap_leak",
                title="Event Listener Retained Heap Leak",
                category="APPLICATION_MEMORY",
                description="Unregistered WebSocket event listener references retaining objects in heap",
                is_ground_truth=True,
                expected_confidence_min=0.85,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["memory_mb", "gc_pause_time_ms"],
            )
        ],
        ground_truth_root_cause="Event Listener Retained Heap Leak",
        remediation=ScenarioRemediationRequirement(
            recommended_action="restart_pod",
            target_service="order-service",
            parameters={"strategy": "rolling_restart", "batch_size": 1},
            requires_human_approval=False,
            risk_score=0.20,
            alternative_actions=["scale_service"],
        ),
        verification=ScenarioVerificationCondition(
            target_service="order-service",
            metric_to_check="memory_mb",
            expected_threshold=600.0,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 3. Database Connection Exhaustion
    # --------------------------------------------------------------------------
    "db_connection_exhaustion": IncidentBenchmarkScenario(
        scenario_id="db_connection_exhaustion",
        name="PostgreSQL Connection Pool Starvation",
        category="DATABASE_EXHAUSTION",
        severity="SEV-1",
        target_service="postgres",
        affected_services=["postgres", "order-service", "payment-service"],
        description="Leaked connection handles from unclosed sessions exhaust max_connections (100/100).",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="postgres",
                baseline_cpu_percent=15.0,
                baseline_memory_mb=1024.0,
                baseline_latency_ms=5.0,
                baseline_error_rate=0.000,
                active_instances=1,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="active_connections",
                target_service="postgres",
                observed_value=100.0,
                threshold_value=90.0,
                unit="count",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="connection_wait_duration_ms",
                target_service="order-service",
                observed_value=5000.0,
                threshold_value=500.0,
                unit="ms",
                anomaly_type="LATENCY_BREACH",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="postgres",
                level="FATAL",
                message_pattern="sorry, too many clients already: max_connections exceeded",
                occurrences_per_min=210,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="POOL_FILL", source_service="postgres", description="Client connections reached 100/100", severity="WARNING"),
            ScenarioTimelineItem(offset_seconds=15, event_type="CLIENT_TIMEOUT", source_service="order-service", description="Pool checkout timed out after 5000ms", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_conn_leak",
                title="PostgreSQL Client Pool Exhaustion from Leaked Handles",
                category="DATABASE",
                description="Client application threads not returning connections on exception blocks",
                is_ground_truth=True,
                expected_confidence_min=0.88,
                expected_confidence_max=0.98,
                supporting_evidence_keys=["active_connections", "connection_wait_duration_ms"],
            )
        ],
        ground_truth_root_cause="PostgreSQL Client Pool Exhaustion from Leaked Handles",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="postgres",
            parameters={"terminate_idle_connections": True, "max_connections": 250},
            requires_human_approval=True,
            risk_score=0.45,
            alternative_actions=["restart_pod"],
        ),
        verification=ScenarioVerificationCondition(
            target_service="postgres",
            metric_to_check="active_connections",
            expected_threshold=45.0,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 4. API Latency Spike
    # --------------------------------------------------------------------------
    "api_latency_spike": IncidentBenchmarkScenario(
        scenario_id="api_latency_spike",
        name="API Gateway P99 Latency Degradation",
        category="NETWORK_PERFORMANCE",
        severity="SEV-2",
        target_service="api-gateway",
        affected_services=["api-gateway", "order-service"],
        description="Downstream upstream timeout misconfiguration stalls API Gateway event loop.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="api-gateway",
                baseline_cpu_percent=10.0,
                baseline_memory_mb=256.0,
                baseline_latency_ms=22.0,
                baseline_error_rate=0.001,
                active_instances=3,
                dependencies=["order-service", "payment-service"],
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="p99_latency_ms",
                target_service="api-gateway",
                observed_value=1850.0,
                threshold_value=150.0,
                unit="ms",
                anomaly_type="LATENCY_BREACH",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="api-gateway",
                level="WARN",
                message_pattern="Upstream proxy response delayed: downstream client connection lagging",
                occurrences_per_min=80,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="LATENCY_SURGE", source_service="api-gateway", description="P99 latency spiked over 1800ms", severity="WARNING")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_downstream_stall",
                title="Upstream Proxy Buffer Saturation",
                category="GATEWAY",
                description="Gateway event loop blocked waiting for lagging backend responses",
                is_ground_truth=True,
                expected_confidence_min=0.75,
                expected_confidence_max=0.92,
                supporting_evidence_keys=["p99_latency_ms"],
            )
        ],
        ground_truth_root_cause="Upstream Proxy Buffer Saturation",
        remediation=ScenarioRemediationRequirement(
            recommended_action="scale_service",
            target_service="api-gateway",
            parameters={"replicas": 5},
            requires_human_approval=False,
            risk_score=0.15,
        ),
        verification=ScenarioVerificationCondition(
            target_service="api-gateway",
            metric_to_check="p99_latency_ms",
            expected_threshold=100.0,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 5. Network Packet Loss
    # --------------------------------------------------------------------------
    "network_packet_loss": IncidentBenchmarkScenario(
        scenario_id="network_packet_loss",
        name="Inter-Service Network Flapping & Packet Loss",
        category="NETWORK_INFRASTRUCTURE",
        severity="SEV-2",
        target_service="order-service",
        affected_services=["order-service", "payment-service"],
        description="Virtual interface MTU mismatch causes 35% packet loss between Order and Payment.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="order-service",
                baseline_cpu_percent=14.0,
                baseline_memory_mb=400.0,
                baseline_latency_ms=25.0,
                baseline_error_rate=0.000,
                active_instances=2,
                dependencies=["payment-service"],
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="packet_drop_rate",
                target_service="order-service",
                observed_value=0.35,
                threshold_value=0.01,
                unit="ratio",
                anomaly_type="DROP",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="tcp_retransmits",
                target_service="order-service",
                observed_value=1240.0,
                threshold_value=50.0,
                unit="count",
                anomaly_type="SPIKE",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="order-service",
                level="ERROR",
                message_pattern="TCP connection reset by peer / retransmission timeout",
                occurrences_per_min=95,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="NETWORK_DROP", source_service="order-service", description="Packet drop exceeded 30%", severity="WARNING")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_packet_loss",
                title="Network Interface Packet Drop & TCP Retransmit Storm",
                category="NETWORKING",
                description="Packet loss caused by network bridge degradation or MTU mismatch",
                is_ground_truth=True,
                expected_confidence_min=0.82,
                expected_confidence_max=0.96,
                supporting_evidence_keys=["packet_drop_rate", "tcp_retransmits"],
            )
        ],
        ground_truth_root_cause="Network Interface Packet Drop & TCP Retransmit Storm",
        remediation=ScenarioRemediationRequirement(
            recommended_action="restart_pod",
            target_service="order-service",
            parameters={"rebind_network_interfaces": True},
            requires_human_approval=False,
            risk_score=0.25,
        ),
        verification=ScenarioVerificationCondition(
            target_service="order-service",
            metric_to_check="packet_drop_rate",
            expected_threshold=0.02,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 6. Service Dependency Failure
    # --------------------------------------------------------------------------
    "service_dependency_failure": IncidentBenchmarkScenario(
        scenario_id="service_dependency_failure",
        name="Auth Service Downstream Dependency Outage (HTTP 503)",
        category="DEPENDENCY_FAILURE",
        severity="SEV-1",
        target_service="auth-service",
        affected_services=["auth-service", "api-gateway", "order-service"],
        description="Auth service crash loops; API Gateway rejects all incoming requests with 503.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="auth-service",
                baseline_cpu_percent=8.0,
                baseline_memory_mb=180.0,
                baseline_latency_ms=15.0,
                baseline_error_rate=0.000,
                active_instances=2,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="http_5xx_rate",
                target_service="auth-service",
                observed_value=0.88,
                threshold_value=0.05,
                unit="ratio",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="api-gateway",
                level="FATAL",
                message_pattern="Dependency 'auth-service' unreachable: 503 Service Unavailable",
                occurrences_per_min=320,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="SERVICE_CRASH", source_service="auth-service", description="Process terminated with SIGSEGV", severity="CRITICAL")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_auth_crash",
                title="Critical Auth Service Process Failure",
                category="SERVICE_CRASH",
                description="Core authentication daemon crashed causing systemwide authorization blackout",
                is_ground_truth=True,
                expected_confidence_min=0.90,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["http_5xx_rate"],
            )
        ],
        ground_truth_root_cause="Critical Auth Service Process Failure",
        remediation=ScenarioRemediationRequirement(
            recommended_action="restart_pod",
            target_service="auth-service",
            parameters={"force": True},
            requires_human_approval=False,
            risk_score=0.20,
        ),
        verification=ScenarioVerificationCondition(
            target_service="auth-service",
            metric_to_check="http_5xx_rate",
            expected_threshold=0.02,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 7. Deployment-Induced Outage
    # --------------------------------------------------------------------------
    "deployment_induced_outage": IncidentBenchmarkScenario(
        scenario_id="deployment_induced_outage",
        name="Deployment Regression in Inventory Service (v2.4.1)",
        category="DEPLOYMENT_FAILURE",
        severity="SEV-1",
        target_service="inventory-service",
        affected_services=["inventory-service", "order-service"],
        description="Canary deployment v2.4.1 introduces unhandled NullReferenceException in catalog parser.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="inventory-service",
                baseline_cpu_percent=12.0,
                baseline_memory_mb=350.0,
                baseline_latency_ms=18.0,
                baseline_error_rate=0.000,
                active_instances=2,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="http_5xx_rate",
                target_service="inventory-service",
                observed_value=0.94,
                threshold_value=0.02,
                unit="ratio",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="inventory-service",
                level="FATAL",
                message_pattern="NullPointerException in CatalogParser.java:42 during startup",
                occurrences_per_min=280,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="DEPLOY_RELEASE", source_service="inventory-service", description="Deployed container image tag v2.4.1", severity="INFO"),
            ScenarioTimelineItem(offset_seconds=10, event_type="ERROR_SURGE", source_service="inventory-service", description="5xx errors jumped to 94%", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_deploy_bug",
                title="Release v2.4.1 Code Regression & Startup Crash",
                category="SOFTWARE_DEFECT",
                description="Faulty code release deploying unhandled exception immediately following rollout",
                is_ground_truth=True,
                expected_confidence_min=0.92,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["http_5xx_rate"],
            )
        ],
        ground_truth_root_cause="Release v2.4.1 Code Regression & Startup Crash",
        remediation=ScenarioRemediationRequirement(
            recommended_action="rollback_deployment",
            target_service="inventory-service",
            parameters={"target_revision": "v2.4.0"},
            requires_human_approval=True,
            risk_score=0.35,
        ),
        verification=ScenarioVerificationCondition(
            target_service="inventory-service",
            metric_to_check="http_5xx_rate",
            expected_threshold=0.01,
            operator="LTE",
            stabilization_window_seconds=15,
        ),
    ),

    # --------------------------------------------------------------------------
    # 8. Database Deadlock
    # --------------------------------------------------------------------------
    "database_deadlock": IncidentBenchmarkScenario(
        scenario_id="database_deadlock",
        name="Cross-Table Row Lock Deadlock Contention",
        category="DATABASE_LOCK",
        severity="SEV-2",
        target_service="postgres",
        affected_services=["postgres", "order-service", "inventory-service"],
        description="Concurrent updates to order items and inventory reservations produce mutual lock cycles.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="postgres",
                baseline_cpu_percent=15.0,
                baseline_memory_mb=1024.0,
                baseline_latency_ms=6.0,
                baseline_error_rate=0.000,
                active_instances=1,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="deadlock_count",
                target_service="postgres",
                observed_value=84.0,
                threshold_value=1.0,
                unit="count",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="postgres",
                level="ERROR",
                message_pattern="ERROR 40P01: deadlock detected between process 14212 and 14219",
                occurrences_per_min=55,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="LOCK_CYCLE", source_service="postgres", description="Deadlock detector triggered 84 times", severity="WARNING")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_deadlock",
                title="Mutual Row-Level Lock Order Inversion",
                category="DATABASE",
                description="Inverse locking order between order creation and inventory decrement transactions",
                is_ground_truth=True,
                expected_confidence_min=0.86,
                expected_confidence_max=0.98,
                supporting_evidence_keys=["deadlock_count"],
            )
        ],
        ground_truth_root_cause="Mutual Row-Level Lock Order Inversion",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="postgres",
            parameters={"terminate_blocking_queries": True},
            requires_human_approval=True,
            risk_score=0.40,
        ),
        verification=ScenarioVerificationCondition(
            target_service="postgres",
            metric_to_check="deadlock_count",
            expected_threshold=0.0,
            operator="EQ",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 9. Traffic Overload
    # --------------------------------------------------------------------------
    "traffic_overload": IncidentBenchmarkScenario(
        scenario_id="traffic_overload",
        name="Volumetric Flash Crowd & Ingress Buffer Saturation",
        category="TRAFFIC_SURGE",
        severity="SEV-2",
        target_service="api-gateway",
        affected_services=["api-gateway", "order-service", "payment-service"],
        description="Promotional marketing campaign causes sudden 500% request volume spike.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="api-gateway",
                baseline_cpu_percent=15.0,
                baseline_memory_mb=256.0,
                baseline_latency_ms=20.0,
                baseline_error_rate=0.001,
                active_instances=3,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="requests_per_sec",
                target_service="api-gateway",
                observed_value=5200.0,
                threshold_value=1200.0,
                unit="rps",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="http_429_rate",
                target_service="api-gateway",
                observed_value=0.28,
                threshold_value=0.01,
                unit="ratio",
                anomaly_type="SPIKE",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="api-gateway",
                level="WARN",
                message_pattern="RateLimiter: Ingress limit exceeded. Throttling client requests.",
                occurrences_per_min=450,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="TRAFFIC_SPIKE", source_service="api-gateway", description="Inbound requests jumped from 1000 to 5200 rps", severity="WARNING")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_flash_crowd",
                title="Volumetric Flash Traffic Exceeding Provisioned Capacity",
                category="TRAFFIC",
                description="Legitimate consumer demand surge outpacing standard auto-scaling velocity",
                is_ground_truth=True,
                expected_confidence_min=0.88,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["requests_per_sec", "http_429_rate"],
            )
        ],
        ground_truth_root_cause="Volumetric Flash Traffic Exceeding Provisioned Capacity",
        remediation=ScenarioRemediationRequirement(
            recommended_action="scale_service",
            target_service="api-gateway",
            parameters={"replicas": 8},
            requires_human_approval=False,
            risk_score=0.20,
        ),
        verification=ScenarioVerificationCondition(
            target_service="api-gateway",
            metric_to_check="http_429_rate",
            expected_threshold=0.02,
            operator="LTE",
            stabilization_window_seconds=15,
        ),
    ),

    # --------------------------------------------------------------------------
    # 10. Cascading Microservice Failure
    # --------------------------------------------------------------------------
    "cascading_microservice_failure": IncidentBenchmarkScenario(
        scenario_id="cascading_microservice_failure",
        name="Multi-Tier Cascading Collapse (Redis -> Inventory -> Order)",
        category="CASCADING_FAILURE",
        severity="SEV-1",
        target_service="redis",
        affected_services=["redis", "inventory-service", "order-service", "api-gateway"],
        description="Redis saturation causes inventory lookup timeouts, exhausting order thread workers.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="redis",
                baseline_cpu_percent=10.0,
                baseline_memory_mb=256.0,
                baseline_latency_ms=1.5,
                baseline_error_rate=0.000,
                active_instances=1,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="redis_connected_clients",
                target_service="redis",
                observed_value=10000.0,
                threshold_value=2000.0,
                unit="count",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="http_5xx_rate",
                target_service="order-service",
                observed_value=0.72,
                threshold_value=0.02,
                unit="ratio",
                anomaly_type="SPIKE",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="inventory-service",
                level="ERROR",
                message_pattern="RedisTimeoutException: Command timed out after 3000ms",
                occurrences_per_min=180,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="REDIS_SATURATION", source_service="redis", description="Client connections exhausted", severity="WARNING"),
            ScenarioTimelineItem(offset_seconds=15, event_type="TIER_COLLAPSE", source_service="inventory-service", description="Inventory latency spiked to 4000ms", severity="CRITICAL"),
            ScenarioTimelineItem(offset_seconds=30, event_type="GATEWAY_DROP", source_service="api-gateway", description="Order checkout failing with 502/504", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_cascading_collapse",
                title="Distributed Cascading Failure Propagating from Cache Tier",
                category="CASCADING",
                description="Unbounded cache client contention cascading upstream to critical transaction flows",
                is_ground_truth=True,
                expected_confidence_min=0.85,
                expected_confidence_max=0.97,
                supporting_evidence_keys=["redis_connected_clients", "http_5xx_rate"],
            )
        ],
        ground_truth_root_cause="Distributed Cascading Failure Propagating from Cache Tier",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="redis",
            parameters={"flush": True, "reset_connections": True},
            requires_human_approval=True,
            risk_score=0.45,
        ),
        verification=ScenarioVerificationCondition(
            target_service="redis",
            metric_to_check="redis_connected_clients",
            expected_threshold=1500.0,
            operator="LTE",
            stabilization_window_seconds=15,
        ),
    ),

    # --------------------------------------------------------------------------
    # 11. Authentication Service Failure
    # --------------------------------------------------------------------------
    "auth_service_failure": IncidentBenchmarkScenario(
        scenario_id="auth_service_failure",
        name="JWT Verification Key Mismatch & Global 401 Cascade",
        category="SECURITY_FAILURE",
        severity="SEV-1",
        target_service="auth-service",
        affected_services=["auth-service", "api-gateway"],
        description="Public key rotation sync failure causes all microservices to reject valid user JWTs.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="auth-service",
                baseline_cpu_percent=12.0,
                baseline_memory_mb=200.0,
                baseline_latency_ms=10.0,
                baseline_error_rate=0.001,
                active_instances=2,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="http_401_rate",
                target_service="api-gateway",
                observed_value=0.91,
                threshold_value=0.01,
                unit="ratio",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="api-gateway",
                level="ERROR",
                message_pattern="JWT signature verification failed: signature does not match public key ID 'key-2026-v2'",
                occurrences_per_min=500,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="KEY_ROTATION", source_service="auth-service", description="Automated key rotation executed", severity="INFO"),
            ScenarioTimelineItem(offset_seconds=5, event_type="AUTH_REJECTION", source_service="api-gateway", description="401 Unauthorized rate spiked to 91%", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_key_mismatch",
                title="Cryptographic Token Signing Key Rotation Desynchronization",
                category="AUTHENTICATION",
                description="Gateway verifying tokens against stale JWKS cache following key rotation",
                is_ground_truth=True,
                expected_confidence_min=0.90,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["http_401_rate"],
            )
        ],
        ground_truth_root_cause="Cryptographic Token Signing Key Rotation Desynchronization",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="api-gateway",
            parameters={"flush_jwks_cache": True},
            requires_human_approval=False,
            risk_score=0.15,
        ),
        verification=ScenarioVerificationCondition(
            target_service="api-gateway",
            metric_to_check="http_401_rate",
            expected_threshold=0.02,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 12. Disk Exhaustion
    # --------------------------------------------------------------------------
    "disk_exhaustion": IncidentBenchmarkScenario(
        scenario_id="disk_exhaustion",
        name="Database Persistent Storage Volume Exhaustion",
        category="STORAGE_FAILURE",
        severity="SEV-1",
        target_service="postgres",
        affected_services=["postgres", "order-service"],
        description="Unpurged database WAL archives fill persistent disk volume to 99.8%.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="postgres",
                baseline_cpu_percent=14.0,
                baseline_memory_mb=1024.0,
                baseline_latency_ms=6.0,
                baseline_error_rate=0.000,
                active_instances=1,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="disk_utilization_percent",
                target_service="postgres",
                observed_value=99.8,
                threshold_value=85.0,
                unit="percent",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="postgres",
                level="FATAL",
                message_pattern="could not write to file 'pg_wal/xlogtemp': No space left on device",
                occurrences_per_min=120,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="DISK_FULL", source_service="postgres", description="Volume utilization reached 99.8%", severity="CRITICAL")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_disk_full",
                title="PostgreSQL WAL Volume Storage Exhaustion",
                category="STORAGE",
                description="WAL archive archiving failure preventing segment log cleanup",
                is_ground_truth=True,
                expected_confidence_min=0.91,
                expected_confidence_max=0.99,
                supporting_evidence_keys=["disk_utilization_percent"],
            )
        ],
        ground_truth_root_cause="PostgreSQL WAL Volume Storage Exhaustion",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="postgres",
            parameters={"purge_archived_wal": True, "vacuum_temp_files": True},
            requires_human_approval=True,
            risk_score=0.40,
        ),
        verification=ScenarioVerificationCondition(
            target_service="postgres",
            metric_to_check="disk_utilization_percent",
            expected_threshold=75.0,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 13. Cache Failure
    # --------------------------------------------------------------------------
    "cache_failure": IncidentBenchmarkScenario(
        scenario_id="cache_failure",
        name="Redis Cache Node Crash & Database Query Stampede",
        category="CACHE_FAILURE",
        severity="SEV-2",
        target_service="redis",
        affected_services=["redis", "postgres", "inventory-service"],
        description="Redis crash causes 100% cache misses, stampeding PostgreSQL with full table scans.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="redis",
                baseline_cpu_percent=8.0,
                baseline_memory_mb=200.0,
                baseline_latency_ms=1.2,
                baseline_error_rate=0.000,
                active_instances=1,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="cache_miss_rate",
                target_service="redis",
                observed_value=1.00,
                threshold_value=0.10,
                unit="ratio",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="cpu_utilization",
                target_service="postgres",
                observed_value=96.4,
                threshold_value=50.0,
                unit="percent",
                anomaly_type="HIGH_UTILIZATION",
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="inventory-service",
                level="WARN",
                message_pattern="Redis connection refused on 6379; falling back to relational database queries",
                occurrences_per_min=310,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="NODE_CRASH", source_service="redis", description="Redis server process crashed", severity="CRITICAL"),
            ScenarioTimelineItem(offset_seconds=10, event_type="DB_STAMPEDE", source_service="postgres", description="PostgreSQL CPU jumped to 96% under cache stampede", severity="WARNING"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_cache_crash",
                title="Distributed Cache Daemon Crash with Secondary DB Stampede",
                category="CACHE",
                description="Unavailability of in-memory caching layer transferring load directly to relational database",
                is_ground_truth=True,
                expected_confidence_min=0.87,
                expected_confidence_max=0.98,
                supporting_evidence_keys=["cache_miss_rate", "cpu_utilization"],
            )
        ],
        ground_truth_root_cause="Distributed Cache Daemon Crash with Secondary DB Stampede",
        remediation=ScenarioRemediationRequirement(
            recommended_action="restart_pod",
            target_service="redis",
            parameters={"prewarm_cache": True},
            requires_human_approval=False,
            risk_score=0.25,
        ),
        verification=ScenarioVerificationCondition(
            target_service="redis",
            metric_to_check="cache_miss_rate",
            expected_threshold=0.15,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),

    # --------------------------------------------------------------------------
    # 14. Multiple Simultaneous Incidents
    # --------------------------------------------------------------------------
    "simultaneous_incidents": IncidentBenchmarkScenario(
        scenario_id="simultaneous_incidents",
        name="Co-Occurring Fault: Payment CPU Saturation + DB Pool Exhaustion",
        category="MULTI_FAULT",
        severity="SEV-1",
        target_service="payment-service",
        affected_services=["payment-service", "postgres", "order-service"],
        description="Dual fault: Payment cryptographic loop saturates CPU while an unclosed loop exhausts PostgreSQL connections.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="payment-service",
                baseline_cpu_percent=18.0,
                baseline_memory_mb=512.0,
                baseline_latency_ms=45.0,
                baseline_error_rate=0.001,
                active_instances=2,
            ),
            ScenarioInfrastructureCondition(
                service_name="postgres",
                baseline_cpu_percent=14.0,
                baseline_memory_mb=1024.0,
                baseline_latency_ms=6.0,
                baseline_error_rate=0.000,
                active_instances=1,
            ),
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="cpu_utilization",
                target_service="payment-service",
                observed_value=98.5,
                threshold_value=80.0,
                unit="percent",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            ),
            ScenarioMetricEvidence(
                metric_name="active_connections",
                target_service="postgres",
                observed_value=99.0,
                threshold_value=90.0,
                unit="count",
                anomaly_type="HIGH_UTILIZATION",
                is_primary_symptom=True,
            ),
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="payment-service",
                level="ERROR",
                message_pattern="Compute starving while database pool full",
                occurrences_per_min=190,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="FAULT_1", source_service="payment-service", description="Payment CPU crossed 95%", severity="WARNING"),
            ScenarioTimelineItem(offset_seconds=10, event_type="FAULT_2", source_service="postgres", description="PostgreSQL client connections hit max", severity="CRITICAL"),
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_dual_fault",
                title="Co-Occurring Dual Infrastructure Fault: Compute + Database",
                category="MULTI_FAULT",
                description="Compound incident involving concurrent independent bottlenecks in compute and database pools",
                is_ground_truth=True,
                expected_confidence_min=0.80,
                expected_confidence_max=0.95,
                supporting_evidence_keys=["cpu_utilization", "active_connections"],
            )
        ],
        ground_truth_root_cause="Co-Occurring Dual Infrastructure Fault: Compute + Database",
        remediation=ScenarioRemediationRequirement(
            recommended_action="scale_service",
            target_service="payment-service",
            parameters={"replicas": 4, "clean_db_pool": True},
            requires_human_approval=True,
            risk_score=0.45,
        ),
        verification=ScenarioVerificationCondition(
            target_service="payment-service",
            metric_to_check="cpu_utilization",
            expected_threshold=70.0,
            operator="LTE",
            stabilization_window_seconds=15,
        ),
    ),

    # --------------------------------------------------------------------------
    # 15. Unknown or Ambiguous Incident
    # --------------------------------------------------------------------------
    "ambiguous_incident": IncidentBenchmarkScenario(
        scenario_id="ambiguous_incident",
        name="Noisy Telemetry Jitter & Intermittent 502 Anomalies",
        category="AMBIGUOUS",
        severity="SEV-3",
        target_service="api-gateway",
        affected_services=["api-gateway", "order-service"],
        description="Sporadic sub-second network jitter with inconsistent error spikes, testing agent uncertainty calibration.",
        initial_conditions=[
            ScenarioInfrastructureCondition(
                service_name="api-gateway",
                baseline_cpu_percent=15.0,
                baseline_memory_mb=256.0,
                baseline_latency_ms=25.0,
                baseline_error_rate=0.002,
                active_instances=3,
            )
        ],
        metric_evidence=[
            ScenarioMetricEvidence(
                metric_name="http_5xx_rate",
                target_service="api-gateway",
                observed_value=0.065,
                threshold_value=0.05,
                unit="ratio",
                anomaly_type="SPIKE",
                is_primary_symptom=True,
            )
        ],
        log_evidence=[
            ScenarioLogEvidence(
                service_name="api-gateway",
                level="WARN",
                message_pattern="Intermittent downstream keep-alive socket timeout (non-deterministic)",
                occurrences_per_min=15,
            )
        ],
        timeline=[
            ScenarioTimelineItem(offset_seconds=0, event_type="JITTER", source_service="api-gateway", description="Transient error spike detected", severity="INFO")
        ],
        hypotheses=[
            ScenarioRootCauseHypothesis(
                hypothesis_id="h1_transient_jitter",
                title="Transient Intermittent Network Socket Jitter",
                category="AMBIGUOUS",
                description="Low-confidence transient network anomaly with insufficient evidence for high confidence",
                is_ground_truth=True,
                expected_confidence_min=0.35,
                expected_confidence_max=0.65,
                supporting_evidence_keys=["http_5xx_rate"],
            ),
            ScenarioRootCauseHypothesis(
                hypothesis_id="h2_hardware_fault",
                title="Underlying Hypervisor Host Hardware Degradation",
                category="INFRASTRUCTURE",
                description="Speculative host degradation",
                is_ground_truth=False,
                expected_confidence_min=0.10,
                expected_confidence_max=0.30,
                supporting_evidence_keys=["http_5xx_rate"],
            ),
        ],
        ground_truth_root_cause="Transient Intermittent Network Socket Jitter",
        remediation=ScenarioRemediationRequirement(
            recommended_action="clear_cache",
            target_service="api-gateway",
            parameters={"flush_dns_cache": True},
            requires_human_approval=False,
            risk_score=0.10,
        ),
        verification=ScenarioVerificationCondition(
            target_service="api-gateway",
            metric_to_check="http_5xx_rate",
            expected_threshold=0.01,
            operator="LTE",
            stabilization_window_seconds=10,
        ),
    ),
}


def get_scenario(scenario_id: str) -> Optional[IncidentBenchmarkScenario]:
    """Retrieves a scenario by ID."""
    return BENCHMARK_SCENARIOS_LIBRARY.get(scenario_id)


def list_all_scenarios() -> List[Dict[str, Any]]:
    """Returns overview metadata for all 15 benchmark scenarios."""
    return [
        {
            "scenario_id": s.scenario_id,
            "name": s.name,
            "category": s.category,
            "severity": s.severity,
            "target_service": s.target_service,
            "affected_services": s.affected_services,
            "description": s.description,
            "ground_truth_root_cause": s.ground_truth_root_cause,
            "recommended_action": s.remediation.recommended_action,
            "requires_human_approval": s.remediation.requires_human_approval,
            "risk_score": s.remediation.risk_score,
        }
        for s in BENCHMARK_SCENARIOS_LIBRARY.values()
    ]
