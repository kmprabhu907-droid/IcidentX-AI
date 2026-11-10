"""
INCIDENTX AI - Multi-Signal Incident Correlation Engine
Groups discrete anomaly alerts, error logs, and trace spans across time windows,
service dependencies, and causal paths into deduplicated, severity-rated incident candidates.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.logging import logger
from backend.app.services.observability.detectors.models import (
    AlertSeverity,
    AnomalyAlert,
)


class CorrelatedIncidentCandidate:
    """Represents a fully synthesized incident candidate ready for automated creation."""
    def __init__(
        self,
        dedup_key: str,
        title: str,
        summary: str,
        severity: str,  # SEV-1, SEV-2, SEV-3, SEV-4
        culprit_service: str,
        impacted_services: List[str],
        evidence_items: List[Dict[str, Any]],
        hypothesis_text: str,
        confidence_score: float,
        data_source: str = "LIVE",
    ):
        self.dedup_key = dedup_key
        self.title = title
        self.summary = summary
        self.severity = severity
        self.culprit_service = culprit_service
        self.impacted_services = impacted_services
        self.evidence_items = evidence_items
        self.hypothesis_text = hypothesis_text
        self.confidence_score = round(confidence_score, 2)
        self.data_source = data_source
        self.created_at = datetime.now(timezone.utc)


class CorrelationEngine:
    """
    Multi-Signal Incident Correlation Engine.
    Uses topological service graphs, temporal windows, and error signatures
    to pinpoint root cause culprits and prevent alert storm fatigue.
    """

    # Service dependency graph (source -> targets it depends on)
    DEPENDENCIES = {
        "api-gateway": ["auth-service", "order-service", "inventory-service"],
        "order-service": ["payment-service", "inventory-service", "postgres-db"],
        "payment-service": ["postgres-db"],
        "inventory-service": ["postgres-db", "redis-cache"],
        "auth-service": ["redis-cache", "postgres-db"],
        "postgres-db": [],
        "redis-cache": [],
    }

    # Service tier definitions
    SERVICE_TIERS = {
        "api-gateway": "Tier-1",
        "auth-service": "Tier-1",
        "order-service": "Tier-1",
        "payment-service": "Tier-1",
        "postgres-db": "Tier-1",
        "inventory-service": "Tier-2",
        "redis-cache": "Tier-2",
    }

    def __init__(self, cooldown_seconds: int = 180):
        self.cooldown_seconds = cooldown_seconds
        # Tracks active dedup_key -> created_at timestamp
        self._active_incident_keys: Dict[str, datetime] = {}

    def correlate(
        self,
        alerts: List[AnomalyAlert],
        recent_logs: Optional[List[Dict[str, Any]]] = None,
        recent_traces: Optional[List[Dict[str, Any]]] = None,
    ) -> List[CorrelatedIncidentCandidate]:
        """
        Correlate a batch of recent alerts into synthesized incident candidates.
        """
        if not alerts:
            return []

        recent_logs = recent_logs or []
        recent_traces = recent_traces or []
        candidates: List[CorrelatedIncidentCandidate] = []

        # 1. Group alerts by service and affected subgraph
        services_with_alerts = {a.service_name for a in alerts}
        now = datetime.now(timezone.utc)

        # Check for simulated vs live
        data_source = "SIMULATED" if any(a.data_source == "SIMULATED" for a in alerts) else "LIVE"

        # 2. Cluster related alerts using topological reachability
        clusters = self._cluster_by_topology(services_with_alerts, alerts)

        for cluster_services, cluster_alerts in clusters:
            # Determine root cause culprit service
            culprit = self._find_root_culprit(cluster_services, cluster_alerts)
            
            # Determine primary anomaly type and error signatures
            primary_anomaly = self._identify_primary_anomaly(culprit, cluster_alerts)

            # Generate deterministic deduplication key
            # Uses 3-minute time buckets to prevent re-alerting on the same incident
            bucket = int(now.timestamp() // self.cooldown_seconds)
            dedup_raw = f"{culprit}:{primary_anomaly}:{bucket}"
            dedup_key = hashlib.sha256(dedup_raw.encode("utf-8")).hexdigest()[:16]

            # Check if this incident was recently triggered
            if self._is_dedup_active(culprit, primary_anomaly, now):
                logger.debug(f"[CorrelationEngine] Skipping deduplicated incident for {culprit} ({primary_anomaly})")
                continue

            # Determine severity
            severity, title, summary, hypothesis, confidence = self._synthesize_incident(
                culprit=culprit,
                cluster_services=cluster_services,
                alerts=cluster_alerts,
                primary_anomaly=primary_anomaly,
                logs=recent_logs,
                traces=recent_traces,
            )

            # Collect Evidence exhibits
            evidence_items = self._build_evidence(cluster_alerts, recent_logs, recent_traces, culprit)

            candidate = CorrelatedIncidentCandidate(
                dedup_key=dedup_key,
                title=title,
                summary=summary,
                severity=severity,
                culprit_service=culprit,
                impacted_services=list(cluster_services),
                evidence_items=evidence_items,
                hypothesis_text=hypothesis,
                confidence_score=confidence,
                data_source=data_source,
            )

            # Register key in cooldown cache
            self._register_incident_key(culprit, primary_anomaly, now)
            candidates.append(candidate)

        return candidates

    def _cluster_by_topology(
        self,
        services: Set[str],
        alerts: List[AnomalyAlert]
    ) -> List[Tuple[Set[str], List[AnomalyAlert]]]:
        """
        Group services into connected components based on dependency topology.
        """
        # Build undirected graph of active alerting services
        adj: Dict[str, Set[str]] = {s: set() for s in services}
        for s1 in services:
            deps = self.DEPENDENCIES.get(s1, [])
            for s2 in deps:
                if s2 in services:
                    adj[s1].add(s2)
                    adj[s2].add(s1)

        visited: Set[str] = set()
        clusters: List[Tuple[Set[str], List[AnomalyAlert]]] = []

        for svc in services:
            if svc not in visited:
                comp = set()
                queue = [svc]
                visited.add(svc)
                while queue:
                    curr = queue.pop(0)
                    comp.add(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                comp_alerts = [a for a in alerts if a.service_name in comp]
                clusters.append((comp, comp_alerts))

        return clusters

    def _find_root_culprit(self, cluster_services: Set[str], alerts: List[AnomalyAlert]) -> str:
        """
        Identify the root cause service within a cluster by finding the most downstream
        or root dependency showing severe failure.
        """
        if len(cluster_services) == 1:
            return next(iter(cluster_services))

        # Check for deep infrastructure failures first (db, cache)
        if "postgres-db" in cluster_services:
            db_alerts = [a for a in alerts if a.service_name == "postgres-db"]
            if any(a.severity == AlertSeverity.CRITICAL for a in db_alerts):
                return "postgres-db"

        if "redis-cache" in cluster_services:
            redis_alerts = [a for a in alerts if a.service_name == "redis-cache"]
            if any(a.severity == AlertSeverity.CRITICAL for a in redis_alerts):
                return "redis-cache"

        # Check payment service if order service is also failing
        if "payment-service" in cluster_services and "order-service" in cluster_services:
            pay_alerts = [a for a in alerts if a.service_name == "payment-service"]
            if any("latency" in a.metric_name or a.severity == AlertSeverity.CRITICAL for a in pay_alerts):
                return "payment-service"

        # Check inventory service if order service or gateway is failing
        if "inventory-service" in cluster_services and "order-service" in cluster_services:
            inv_alerts = [a for a in alerts if a.service_name == "inventory-service"]
            if any(a.severity == AlertSeverity.CRITICAL for a in inv_alerts):
                return "inventory-service"

        # Otherwise, pick service with earliest or highest severity alert that has no failing dependencies
        scored: List[Tuple[str, int]] = []
        for svc in cluster_services:
            svc_alerts = [a for a in alerts if a.service_name == svc]
            crit_count = sum(1 for a in svc_alerts if a.severity == AlertSeverity.CRITICAL)
            # Penalize services that depend on other failing services in the cluster
            deps = self.DEPENDENCIES.get(svc, [])
            downstream_failing = sum(1 for d in deps if d in cluster_services)
            score = (crit_count * 5) - (downstream_failing * 3)
            scored.append((svc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _identify_primary_anomaly(self, culprit: str, alerts: List[AnomalyAlert]) -> str:
        culprit_alerts = [a for a in alerts if a.service_name == culprit]
        if not culprit_alerts:
            culprit_alerts = alerts

        # Check for specific anomaly types in priority order
        metrics = [a.metric_name for a in culprit_alerts]
        if "db_pool_utilization" in metrics:
            return "db_pool_exhaustion"
        if "latency_p99_ms" in metrics or "latency_p95_ms" in metrics:
            return "latency_spike"
        if "memory_utilization" in metrics:
            return "memory_leak"
        if "cpu_utilization" in metrics:
            return "cpu_spike"
        if "error_rate" in metrics or "exception_cluster" in metrics:
            return "error_rate_surge"
        if "traffic_surge" in metrics:
            return "traffic_surge"
        if "traffic_blackout" in metrics:
            return "traffic_blackout"
        return "system_degradation"

    def _is_dedup_active(self, culprit: str, anomaly: str, now: datetime) -> bool:
        key = f"{culprit}:{anomaly}"
        last_time = self._active_incident_keys.get(key)
        if not last_time:
            return False
        elapsed = (now - last_time).total_seconds()
        return elapsed < self.cooldown_seconds

    def _register_incident_key(self, culprit: str, anomaly: str, now: datetime):
        key = f"{culprit}:{anomaly}"
        self._active_incident_keys[key] = now

    def _synthesize_incident(
        self,
        culprit: str,
        cluster_services: Set[str],
        alerts: List[AnomalyAlert],
        primary_anomaly: str,
        logs: List[Dict[str, Any]],
        traces: List[Dict[str, Any]],
    ) -> Tuple[str, str, str, str, float]:
        """
        Synthesizes severity, title, executive summary, and courtroom hypothesis.
        """
        has_critical = any(a.severity == AlertSeverity.CRITICAL for a in alerts)
        tier = self.SERVICE_TIERS.get(culprit, "Tier-2")
        impact_count = len(cluster_services)

        # 1. Severity logic
        if primary_anomaly in ["db_pool_exhaustion", "error_rate_surge"] and (tier == "Tier-1" or "api-gateway" in cluster_services):
            severity = "SEV-1"
        elif primary_anomaly == "latency_spike" and "payment-service" in cluster_services:
            severity = "SEV-2"
        elif has_critical or tier == "Tier-1" or impact_count >= 2:
            severity = "SEV-2"
        elif primary_anomaly in ["cpu_spike", "memory_leak"]:
            severity = "SEV-3"
        else:
            severity = "SEV-4"

        # 2. Human-readable titles & summaries
        culprit_title = culprit.replace("-", " ").title()

        if primary_anomaly == "db_pool_exhaustion":
            title = f"{severity}: Critical Database Connection Pool Exhaustion on {culprit_title}"
            summary = (
                f"Autonomous observability detected severe connection pool saturation (100% capacity) on {culprit}. "
                f"Downstream services ({', '.join(cluster_services - {culprit})}) are failing with connection acquisition "
                f"timeouts, triggering widespread transaction rollbacks."
            )
            hypothesis = (
                f"The incident was caused by database connection pool depletion on {culprit}. "
                f"Unreleased connections or long-running transactions exhausted all available worker slots, "
                f"causing cascading timeouts in calling microservices."
            )
            confidence = 0.94

        elif primary_anomaly == "latency_spike":
            title = f"{severity}: Upstream Latency Degradation in {culprit_title}"
            summary = (
                f"P95/P99 response latencies for {culprit} escalated drastically, exceeding critical SLAs. "
                f"Caller services experienced upstream HTTP 504 timeouts on customer-facing flows."
            )
            hypothesis = (
                f"{culprit_title} experienced severe internal processing delay or external PSP gateway latency, "
                f"exceeding client timeout thresholds and propagating 504 Gateway Timeouts up to the API Gateway."
            )
            confidence = 0.91

        elif primary_anomaly == "memory_leak":
            title = f"{severity}: Progressive Memory Saturation and Leak on {culprit_title}"
            summary = (
                f"Memory utilization on {culprit} climbed past critical boundaries without garbage collection recovery, "
                f"inducing stop-the-world pauses and tail latency inflation."
            )
            hypothesis = (
                f"An unbounded memory leak in {culprit} is consuming heap space, causing severe memory pressure "
                f"and risking impending OOM termination."
            )
            confidence = 0.88

        elif primary_anomaly == "cpu_spike":
            title = f"{severity}: CPU Saturation and Thread Starvation on {culprit_title}"
            summary = (
                f"CPU utilization on {culprit} spiked above 95%, causing thread starvation, "
                f"queue backlog expansion, and degraded throughput across connected services."
            )
            hypothesis = (
                f"Sustained high compute load on {culprit} saturated CPU resources, slowing request dispatch "
                f"and causing request queue saturation."
            )
            confidence = 0.89

        elif primary_anomaly == "traffic_surge":
            title = f"{severity}: Unexpected Traffic Surge Saturating {culprit_title}"
            summary = (
                f"Inbound request rate on {culprit} expanded beyond capacity limits, "
                f"saturating network buffers and driving up tail latencies."
            )
            hypothesis = (
                f"A sudden ingress traffic surge exceeded normal capacity thresholds, "
                f"triggering rate limiting and resource contention across {culprit}."
            )
            confidence = 0.87

        else:
            title = f"{severity}: Elevated Error Rate and Degradation on {culprit_title}"
            summary = (
                f"Multiple correlated anomaly alerts detected across {culprit} and {', '.join(cluster_services)}. "
                f"Error rates and latency distributions deviated significantly from baseline expectations."
            )
            hypothesis = (
                f"Internal application exception cascade or regression in {culprit} caused widespread request failures."
            )
            confidence = 0.85

        return severity, title, summary, hypothesis, confidence

    def _build_evidence(
        self,
        alerts: List[AnomalyAlert],
        logs: List[Dict[str, Any]],
        traces: List[Dict[str, Any]],
        culprit: str,
    ) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []

        # 1. Metric anomaly evidence
        for alert in alerts[:4]:
            evidence.append({
                "evidence_type": "metric_anomaly",
                "source_system": "prometheus",
                "description": alert.message,
                "confidence_score": 0.95 if alert.severity == AlertSeverity.CRITICAL else 0.80,
                "is_contradictory": False,
                "raw_data": str(alert.to_dict()),
            })

        # 2. Correlated error logs
        matching_logs = [log for log in logs if log.get("service_name") == culprit and log.get("level") == "ERROR"]
        for log in matching_logs[:3]:
            evidence.append({
                "evidence_type": "error_log",
                "source_system": "loki",
                "description": f"[{log.get('service_name')}] {log.get('message')}",
                "confidence_score": 0.92,
                "is_contradictory": False,
                "raw_data": str(log),
            })

        # 3. Distributed trace exhibits
        failed_traces = [t for t in traces if t.get("has_error") and any(s.get("service_name") == culprit for s in t.get("spans", []))]
        for t in failed_traces[:2]:
            evidence.append({
                "evidence_type": "trace_span",
                "source_system": "opentelemetry",
                "description": f"Trace {t.get('trace_id')[:8]} failed at {culprit} ({t.get('operation_name')}, duration={t.get('duration_ms')}ms)",
                "confidence_score": 0.98,
                "is_contradictory": False,
                "raw_data": str(t),
            })

        return evidence
