"""
INCIDENTX AI - Incident Fingerprinting Module
Constructs a normalized, multi-feature incident fingerprint representation
enabling multi-dimensional similarity matching across historical failure archives.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# Canonical root-cause classification keywords
ROOT_CAUSE_KEYWORD_MAP = {
    "pool": "DATABASE_POOL_EXHAUSTION",
    "connection": "DATABASE_POOL_EXHAUSTION",
    "postgres": "DATABASE_POOL_EXHAUSTION",
    "memory": "MEMORY_LEAK",
    "heap": "MEMORY_LEAK",
    "oom": "MEMORY_LEAK",
    "leak": "MEMORY_LEAK",
    "cpu": "CPU_SATURATION",
    "spike": "CPU_SATURATION",
    "latency": "LATENCY_SPIKE",
    "timeout": "LATENCY_SPIKE",
    "handshake": "TLS_HANDSHAKE_TIMEOUT",
    "tls": "TLS_HANDSHAKE_TIMEOUT",
    "network": "NETWORK_SATURATION",
    "bandwidth": "NETWORK_SATURATION",
    "dependency": "DOWNSTREAM_DEPENDENCY_FAILURE",
    "downstream": "DOWNSTREAM_DEPENDENCY_FAILURE",
    "503": "SERVICE_UNAVAILABLE",
    "504": "GATEWAY_TIMEOUT",
    "config": "CONFIGURATION_DRIFT",
}


def normalize_error_string(raw_error: str) -> str:
    """
    Strips transient runtime parameters such as UUIDs, IP addresses, ports,
    hexadecimal memory pointers, and timestamps from raw error messages.
    """
    if not raw_error:
        return ""
    text = raw_error.lower()
    # Remove UUIDs
    text = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", text)
    # Remove IP addresses and ports
    text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?\b", "<ip>", text)
    # Remove hex addresses
    text = re.sub(r"0x[0-9a-fA-F]+", "<hex>", text)
    # Remove ISO timestamps
    text = re.sub(r"\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}:\d{2}(\.\d+)?(z)?", "<timestamp>", text)
    # Collapse extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_root_cause_categories(text_corpus: List[str]) -> Set[str]:
    """Extracts standardized root-cause taxonomy categories from free-text descriptions."""
    categories: Set[str] = set()
    combined_text = " ".join(text_corpus).lower()
    for keyword, category in ROOT_CAUSE_KEYWORD_MAP.items():
        if keyword in combined_text:
            categories.add(category)
    return categories


@dataclass
class IncidentFingerprint:
    """
    Comprehensive multi-feature representation of an incident.
    """
    incident_id: str
    primary_service: str
    affected_services: Set[str] = field(default_factory=set)
    metric_anomaly_vector: Dict[str, float] = field(default_factory=dict)
    error_signatures: Set[str] = field(default_factory=set)
    root_cause_categories: Set[str] = field(default_factory=set)
    hypotheses_text: List[str] = field(default_factory=list)
    dependency_subgraph: Dict[str, List[str]] = field(default_factory=dict)
    failure_propagation_path: List[str] = field(default_factory=list)
    severity: str = "SEV-2"
    timeline_features: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "primary_service": self.primary_service,
            "affected_services": sorted(list(self.affected_services)),
            "metric_anomaly_vector": {k: round(v, 3) for k, v in self.metric_anomaly_vector.items()},
            "error_signatures": sorted(list(self.error_signatures)),
            "root_cause_categories": sorted(list(self.root_cause_categories)),
            "hypotheses_text": self.hypotheses_text,
            "dependency_subgraph": self.dependency_subgraph,
            "failure_propagation_path": self.failure_propagation_path,
            "severity": self.severity,
            "timeline_features": self.timeline_features,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentFingerprint":
        return cls(
            incident_id=data.get("incident_id", ""),
            primary_service=data.get("primary_service", ""),
            affected_services=set(data.get("affected_services", [])),
            metric_anomaly_vector=data.get("metric_anomaly_vector", {}),
            error_signatures=set(data.get("error_signatures", [])),
            root_cause_categories=set(data.get("root_cause_categories", [])),
            hypotheses_text=data.get("hypotheses_text", []),
            dependency_subgraph=data.get("dependency_subgraph", {}),
            failure_propagation_path=data.get("failure_propagation_path", []),
            severity=data.get("severity", "SEV-2"),
            timeline_features=data.get("timeline_features", {}),
        )


class FingerprintBuilder:
    """
    Builds an IncidentFingerprint from live or historical incident entities.
    """

    @classmethod
    def build(
        cls,
        incident_id: str,
        primary_service: str,
        affected_services: Optional[List[str]] = None,
        telemetry_anomalies: Optional[Dict[str, float]] = None,
        error_logs: Optional[List[str]] = None,
        hypotheses: Optional[List[str]] = None,
        propagation_path: Optional[List[str]] = None,
        topology_deps: Optional[Dict[str, List[str]]] = None,
        severity: str = "SEV-2",
        timeline_features: Optional[Dict[str, Any]] = None,
    ) -> IncidentFingerprint:
        aff_set = set(affected_services or [])
        if primary_service:
            aff_set.add(primary_service)

        # Normalize metric anomaly vector (e.g. z-scores or relative departures)
        anomaly_vector = {k: float(v) for k, v in (telemetry_anomalies or {}).items()}

        # Normalize and deduplicate error signatures
        signatures: Set[str] = set()
        for log_msg in error_logs or []:
            norm = normalize_error_string(log_msg)
            if norm:
                signatures.add(norm)

        # Determine root cause categories
        hypo_list = hypotheses or []
        categories = extract_root_cause_categories(hypo_list + (error_logs or []))

        # Extract local dependency subgraph for the affected services
        all_deps = topology_deps or {
            "api-gateway": ["auth-service", "order-service", "inventory-service"],
            "order-service": ["payment-service", "inventory-service", "postgres-db"],
            "payment-service": ["postgres-db"],
            "inventory-service": ["postgres-db", "redis-cache"],
            "auth-service": ["redis-cache", "postgres-db"],
            "postgres-db": [],
            "redis-cache": [],
        }
        subgraph: Dict[str, List[str]] = {}
        for svc in aff_set:
            if svc in all_deps:
                subgraph[svc] = all_deps[svc]

        return IncidentFingerprint(
            incident_id=incident_id,
            primary_service=primary_service,
            affected_services=aff_set,
            metric_anomaly_vector=anomaly_vector,
            error_signatures=signatures,
            root_cause_categories=categories,
            hypotheses_text=hypo_list,
            dependency_subgraph=subgraph,
            failure_propagation_path=propagation_path or [primary_service],
            severity=severity,
            timeline_features=timeline_features or {},
        )
