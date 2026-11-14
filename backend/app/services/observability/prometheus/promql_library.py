"""
INCIDENTX AI - PromQL Query Library (Phase 8.3)
Curated catalog of battle-tested, parameterized PromQL queries for Kubernetes and microservices.
Enforces safe divisions (clamp_min), rate smoothing, and missing-metric resilience.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PromQLTemplate(BaseModel):
    id: str
    name: str
    category: str  # "CONTAINER", "NETWORK", "APPLICATION", "NODE", "KUBERNETES"
    description: str
    query_template: str
    unit: str
    parameters: List[str]
    default_step: str = "15s"


class PromQLLibrary:
    """
    Registry of parameterized PromQL templates for enterprise SRE investigations.
    """

    TEMPLATES: Dict[str, PromQLTemplate] = {
        # Container Resource Saturation
        "container_cpu_usage": PromQLTemplate(
            id="container_cpu_usage",
            name="Container CPU Utilization Rate",
            category="CONTAINER",
            description="Per-container CPU core usage rate smoothed over 5-minute window.",
            query_template='sum(rate(container_cpu_usage_seconds_total{namespace=~"{namespace}", pod=~"{pod}", container!="", container!="POD"}[5m])) by (pod, container)',
            unit="cores",
            parameters=["namespace", "pod"],
        ),
        "container_memory_working_set": PromQLTemplate(
            id="container_memory_working_set",
            name="Container Memory Working Set Bytes",
            category="CONTAINER",
            description="Memory working set bytes (the metric Kubelet evaluates for OOMKilled events).",
            query_template='sum(container_memory_working_set_bytes{namespace=~"{namespace}", pod=~"{pod}", container!="", container!="POD"}) by (pod, container)',
            unit="bytes",
            parameters=["namespace", "pod"],
        ),
        "container_memory_utilization_percent": PromQLTemplate(
            id="container_memory_utilization_percent",
            name="Container Memory Utilization Percent",
            category="CONTAINER",
            description="Memory usage as a percentage of configured limit (safely clamped to avoid zero division).",
            query_template='100 * (sum(container_memory_working_set_bytes{namespace=~"{namespace}", pod=~"{pod}", container!=""}) by (pod, container) / clamp_min(sum(container_spec_memory_limit_bytes{namespace=~"{namespace}", pod=~"{pod}", container!=""}) by (pod, container), 1048576))',
            unit="percent",
            parameters=["namespace", "pod"],
        ),

        # Network I/O
        "pod_network_receive_rate": PromQLTemplate(
            id="pod_network_receive_rate",
            name="Pod Network Inbound Bytes Rate",
            category="NETWORK",
            description="Rate of inbound bytes received by pod network interface over 5m.",
            query_template='sum(rate(container_network_receive_bytes_total{namespace=~"{namespace}", pod=~"{pod}"}[5m])) by (pod)',
            unit="bytes/sec",
            parameters=["namespace", "pod"],
        ),
        "pod_network_transmit_rate": PromQLTemplate(
            id="pod_network_transmit_rate",
            name="Pod Network Outbound Bytes Rate",
            category="NETWORK",
            description="Rate of outbound bytes transmitted by pod network interface over 5m.",
            query_template='sum(rate(container_network_transmit_bytes_total{namespace=~"{namespace}", pod=~"{pod}"}[5m])) by (pod)',
            unit="bytes/sec",
            parameters=["namespace", "pod"],
        ),

        # Application Golden Signals
        "http_request_rate": PromQLTemplate(
            id="http_request_rate",
            name="Application HTTP Request Rate (RPS)",
            category="APPLICATION",
            description="Total HTTP requests per second partitioned by service.",
            query_template='sum(rate(http_requests_total{service=~"{service}"}[5m])) by (service)',
            unit="rps",
            parameters=["service"],
        ),
        "http_error_rate_percent": PromQLTemplate(
            id="http_error_rate_percent",
            name="Application HTTP 5xx Error Rate Percentage",
            category="APPLICATION",
            description="Percentage of 5xx server errors over total HTTP traffic (with safe zero-denominator clamp).",
            query_template='100 * (sum(rate(http_requests_total{service=~"{service}", status=~"5.."}[5m])) by (service) / clamp_min(sum(rate(http_requests_total{service=~"{service}"}[5m])) by (service), 0.001))',
            unit="percent",
            parameters=["service"],
        ),
        "http_latency_p95": PromQLTemplate(
            id="http_latency_p95",
            name="Application P95 Latency",
            category="APPLICATION",
            description="95th percentile HTTP request duration in milliseconds.",
            query_template='1000 * histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service=~"{service}"}[5m])) by (le, service))',
            unit="ms",
            parameters=["service"],
        ),
        "http_latency_p99": PromQLTemplate(
            id="http_latency_p99",
            name="Application P99 Latency",
            category="APPLICATION",
            description="99th percentile HTTP request duration in milliseconds.",
            query_template='1000 * histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=~"{service}"}[5m])) by (le, service))',
            unit="ms",
            parameters=["service"],
        ),

        # Kubernetes Health & Lifecycle
        "pod_restart_increase_1h": PromQLTemplate(
            id="pod_restart_increase_1h",
            name="Pod Container Restarts in Past Hour",
            category="KUBERNETES",
            description="Number of container restart increments over the past 60 minutes.",
            query_template='sum(increase(kube_pod_container_status_restarts_total{namespace=~"{namespace}", pod=~"{pod}"}[1h])) by (pod)',
            unit="count",
            parameters=["namespace", "pod"],
        ),
        "pods_not_running": PromQLTemplate(
            id="pods_not_running",
            name="Pods in Failed or Pending Phase",
            category="KUBERNETES",
            description="Count of pods whose current phase is not Running.",
            query_template='sum(kube_pod_status_phase{phase!~"Running|Succeeded", namespace=~"{namespace}"}) by (namespace, phase)',
            unit="count",
            parameters=["namespace"],
        ),

        # Node Infrastructure
        "node_cpu_utilization_percent": PromQLTemplate(
            id="node_cpu_utilization_percent",
            name="Cluster Node CPU Utilization Percent",
            category="NODE",
            description="Aggregate CPU core utilization percentage across physical/virtual nodes.",
            query_template='100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance))',
            unit="percent",
            parameters=[],
        ),
        "node_memory_utilization_percent": PromQLTemplate(
            id="node_memory_utilization_percent",
            name="Cluster Node Memory Utilization Percent",
            category="NODE",
            description="Node memory utilization percentage computed from available vs total bytes.",
            query_template='100 * (1 - (node_memory_MemAvailable_bytes / clamp_min(node_memory_MemTotal_bytes, 1048576)))',
            unit="percent",
            parameters=[],
        ),
    }

    @classmethod
    def get_template(cls, template_id: str) -> Optional[PromQLTemplate]:
        return cls.TEMPLATES.get(template_id)

    @classmethod
    def list_templates(cls, category: Optional[str] = None) -> List[PromQLTemplate]:
        if category:
            return [t for t in cls.TEMPLATES.values() if t.category.upper() == category.upper()]
        return list(cls.TEMPLATES.values())

    @classmethod
    def render_query(cls, template_id: str, **kwargs) -> str:
        """
        Fill in template variables with regex-safe defaults.
        """
        template = cls.get_template(template_id)
        if not template:
            raise ValueError(f"Unknown PromQL template ID: {template_id}")

        query = template.query_template
        # Fill in defaults if not provided
        defaults = {
            "namespace": ".*",
            "pod": ".*",
            "service": ".*",
            "container": ".*",
        }
        merged = {**defaults, **kwargs}
        for param, val in merged.items():
            query = query.replace(f"{{{param}}}", str(val))
        return query


# Global singleton instance
promql_library = PromQLLibrary()
