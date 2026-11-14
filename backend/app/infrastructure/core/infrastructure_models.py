"""
INCIDENTX AI - Infrastructure Abstraction Models (Phase 8.1)
Standardized Pydantic models representing unified infrastructure topology, workloads,
health, events, metrics, and environment metadata across DemoMesh and Kubernetes.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EnvironmentMode(str, Enum):
    DEMOMESH = "DEMOMESH"
    KUBERNETES = "KUBERNETES"


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


class WorkloadPhase(str, Enum):
    RUNNING = "RUNNING"
    PENDING = "PENDING"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CRASH_LOOP = "CRASH_LOOP"


class EnvironmentHealth(BaseModel):
    status: str = Field(..., description="HEALTHY, DEGRADED, or UNHEALTHY")
    mode: EnvironmentMode
    latency_ms: float
    is_healthy: bool = True
    active_incidents_or_faults: int = 0
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "SIMULATED"


class InfrastructureService(BaseModel):
    id: str
    name: str
    namespace: Optional[str] = None
    service_type: str = "ClusterIP"
    tier: str = "Tier-1"
    cluster_ip: Optional[str] = None
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints: List[str] = Field(default_factory=list)
    protocol: str = "TCP"
    selectors: Dict[str, str] = Field(default_factory=dict)
    workload_count: int = 1
    data_source: str = "SIMULATED"
    created_at: Optional[str] = None


class InfrastructureWorkload(BaseModel):
    id: str
    name: str
    namespace: Optional[str] = None
    workload_type: str = "Deployment"  # Deployment, Pod, StatefulSet, SimulatedContainer
    kind: str = "Deployment"
    desired_replicas: int = 1
    replicas_desired: int = 1
    ready_replicas: int = 1
    replicas_available: int = 1
    restart_count: int = 0
    status: WorkloadPhase = WorkloadPhase.RUNNING
    phase: str = "Running"
    image: str = "app:latest"
    cpu_request_cores: float = 0.1
    cpu_limit_cores: float = 0.5
    memory_request_mb: float = 128.0
    memory_limit_mb: float = 512.0
    last_termination_reason: Optional[str] = None  # OOMKilled, Error, Completed, None
    labels: Dict[str, str] = Field(default_factory=dict)
    data_source: str = "SIMULATED"
    created_at: Optional[str] = None


class WorkloadStatus(BaseModel):
    workload_id: str
    name: str
    namespace: Optional[str] = None
    phase: WorkloadPhase = WorkloadPhase.RUNNING
    ready: bool = True
    restart_count: int = 0
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    pod_statuses: List[Dict[str, Any]] = Field(default_factory=list)
    data_source: str = "SIMULATED"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InfrastructureEvent(BaseModel):
    id: str
    event_type: str = "Normal"  # Normal, Warning, Anomaly, Incident
    reason: str
    message: str
    source_component: str
    resource_kind: str
    resource_name: str
    namespace: Optional[str] = None
    count: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    first_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "SIMULATED"


class ResourceMetric(BaseModel):
    workload_id: str
    workload_name: str
    namespace: Optional[str] = None
    metric_name: str  # cpu_utilization, memory_utilization, latency_ms, etc.
    value: float
    unit: str  # percent, mb, ms, count
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "SIMULATED"  # "SIMULATED" or "LIVE_K8S"


class EnvironmentMetadata(BaseModel):
    mode: EnvironmentMode
    name: str = "DemoMesh Simulation"
    cluster_name: str
    cluster_version: Optional[str] = None
    api_endpoint: str
    version: str
    connection_status: ConnectionStatus
    is_read_only: bool = True
    is_simulated: bool = False
    data_source: str = "SIMULATED"
    namespaces: List[str] = Field(default_factory=list)
    namespace: Optional[str] = "default"
    node_count: Optional[int] = 1
    total_services: int = 0
    total_workloads: int = 0
    connected_at: Optional[str] = None
    last_sync_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    connection_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 8.2 Kubernetes Cluster Integration Models
# ---------------------------------------------------------------------------

class KubernetesNode(BaseModel):
    name: str
    ready: bool = True
    kubelet_version: str = "v1.30.0"
    os_image: str = "Linux"
    architecture: str = "amd64"
    cpu_allocatable_cores: float = 4.0
    memory_allocatable_mb: float = 8192.0
    conditions: Dict[str, str] = Field(default_factory=lambda: {"Ready": "True", "MemoryPressure": "False", "DiskPressure": "False"})
    labels: Dict[str, str] = Field(default_factory=dict)
    creation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "LIVE_K8S"


class KubernetesNamespace(BaseModel):
    name: str
    status: str = "Active"
    workload_count: int = 0
    creation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    labels: Dict[str, str] = Field(default_factory=dict)
    data_source: str = "LIVE_K8S"


class KubernetesPod(BaseModel):
    name: str
    namespace: str = "default"
    phase: str = "Running"
    ready: bool = True
    restart_count: int = 0
    pod_ip: Optional[str] = None
    node_name: Optional[str] = None
    creation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    containers: List[Dict[str, Any]] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    data_source: str = "LIVE_K8S"


class KubernetesDeployment(BaseModel):
    name: str
    namespace: str = "default"
    desired_replicas: int = 1
    available_replicas: int = 1
    updated_replicas: int = 1
    rollout_status: str = "Healthy"
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    creation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "LIVE_K8S"


class KubernetesService(BaseModel):
    name: str
    namespace: str = "default"
    service_type: str = "ClusterIP"
    cluster_ip: Optional[str] = None
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints_available: int = 1
    selectors: Dict[str, str] = Field(default_factory=dict)
    creation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "LIVE_K8S"


class KubernetesResourceMetrics(BaseModel):
    resource_type: str = "pod"  # "pod", "node", "cluster"
    resource_name: str
    namespace: Optional[str] = None
    configured_cpu_request_cores: float = 0.0
    configured_cpu_limit_cores: float = 0.0
    configured_memory_request_mb: float = 0.0
    configured_memory_limit_mb: float = 0.0
    measured_cpu_cores: Optional[float] = None
    measured_memory_mb: Optional[float] = None
    metrics_server_available: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "LIVE_K8S"


class KubernetesClusterOverview(BaseModel):
    connection_status: str = "DISCONNECTED"  # "CONNECTED", "DISCONNECTED", "ERROR"
    cluster_name: str = "unconfigured"
    kubernetes_version: str = "unknown"
    api_endpoint: str = "none"
    auth_method: str = "none"  # "kubeconfig", "in_cluster_serviceaccount", "bearer_token", "mock_sandbox"
    is_live: bool = False
    is_read_only: bool = True
    total_nodes: int = 0
    ready_nodes: int = 0
    total_namespaces: int = 0
    total_pods: int = 0
    healthy_deployments: int = 0
    metrics_server_available: bool = False
    error_message: Optional[str] = None
    last_sync_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_source: str = "LIVE_K8S"


class KubernetesConnectionDetails(BaseModel):
    cluster_id: str
    cluster_name: str
    api_server_url: str
    auth_method: str
    is_connected: bool
    is_live: bool
    is_read_only: bool = True
    masked_token: Optional[str] = None
    discovered_version: Optional[str] = None
    last_error: Optional[str] = None
    connected_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 8.3 Prometheus, OpenTelemetry & Grafana Observability Models
# ---------------------------------------------------------------------------

class PrometheusHealthStatus(BaseModel):
    status: str = "NOT_CONFIGURED"  # AVAILABLE, UNAVAILABLE, NOT_CONFIGURED, ERROR
    endpoint: str = "http://localhost:9090"
    latency_ms: float = 0.0
    version: Optional[str] = None
    error_message: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PrometheusMetricSeries(BaseModel):
    metric_name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    values: List[List[Any]] = Field(default_factory=list)  # [[timestamp, value_str]]
    latest_value: Optional[float] = None
    unit: str = ""


class PrometheusQueryResult(BaseModel):
    status: str = "SUCCESS"  # SUCCESS, UNAVAILABLE, ERROR, EMPTY
    query: str
    result_type: str = "vector"  # vector, matrix
    series: List[PrometheusMetricSeries] = Field(default_factory=list)
    error_message: Optional[str] = None
    data_source: str = "PROMETHEUS"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PrometheusMetricMetadata(BaseModel):
    metric: str
    type: str = "gauge"
    help: str = ""
    unit: str = ""


class OpenTelemetrySpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    service_name: str
    kind: str = "SPAN_KIND_SERVER"
    start_time_iso: str
    end_time_iso: str
    duration_ms: float
    status_code: str = "OK"  # OK, ERROR, UNSET
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    k8s_namespace: Optional[str] = None
    k8s_pod_name: Optional[str] = None
    k8s_deployment_name: Optional[str] = None
    incident_id: Optional[str] = None
    is_bottleneck: bool = False
    is_error: bool = False
    data_source: str = "OPENTELEMETRY"


class OpenTelemetryTrace(BaseModel):
    trace_id: str
    root_service: str
    root_operation: str
    start_time_iso: str
    duration_ms: float
    span_count: int
    error_count: int
    has_error: bool
    spans: List[OpenTelemetrySpan] = Field(default_factory=list)
    incident_id: Optional[str] = None
    bottleneck_span_id: Optional[str] = None
    data_source: str = "OPENTELEMETRY"


class GrafanaDashboardInfo(BaseModel):
    uid: str
    title: str
    url: str
    tags: List[str] = Field(default_factory=list)
    type: str = "dash-db"
    is_starred: bool = False


class GrafanaAnnotation(BaseModel):
    id: Optional[int] = None
    dashboard_uid: Optional[str] = None
    time_ms: int
    time_end_ms: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    text: str
    created_at: Optional[str] = None


class UnifiedTelemetryTimelineItem(BaseModel):
    id: str
    timestamp: str
    source: str  # PROMETHEUS, OPENTELEMETRY, KUBERNETES, DEMOMESH, INCIDENT
    category: str  # METRIC_ANOMALY, TRACE_FAILURE, K8S_EVENT, APPLICATION_LOG, INCIDENT_STATE
    severity: str = "INFO"  # INFO, WARN, HIGH, CRITICAL
    resource_name: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    data_source: str = "LIVE_K8S"  # LIVE_K8S, SIMULATED
    incident_id: Optional[str] = None


class TelemetryAnomalyRecord(BaseModel):
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metric_name: str
    resource_name: str
    detector_type: str  # STATIC_THRESHOLD, ROLLING_BASELINE, Z_SCORE
    current_value: float
    baseline_value: float
    threshold_value: float
    deviation_sigma: Optional[float] = None
    consecutive_breaches: int = 1
    severity: str = "WARN"
    explanation: str
    data_source: str = "PROMETHEUS"


class ObservabilityStackStatus(BaseModel):
    prometheus: PrometheusHealthStatus
    opentelemetry: Dict[str, Any]
    grafana: Dict[str, Any]
    active_environment_mode: str = "DEMOMESH"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


