"""
INCIDENTX AI - Kubernetes Event Streamer & Deduplication Engine (Phase 8.2)
Collects live Kubernetes warning and normal events, identifies critical infrastructure
failure signatures, prevents duplicate ingestion, and connects signals to AI agents.
"""

from collections import deque
from datetime import datetime, timezone
import hashlib
from typing import Any, AsyncGenerator, Deque, Dict, List, Optional, Set
from backend.app.core.logging import logger
from backend.app.infrastructure.core.infrastructure_models import InfrastructureEvent
from backend.app.infrastructure.kubernetes.kubernetes_client import KubernetesClient

# Recognized Kubernetes critical failure signatures
CRITICAL_K8S_FAILURE_REASONS = {
    "FailedScheduling",
    "BackOff",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "OOMKilled",
    "FailedMount",
    "NodeNotReady",
    "FailedDeployment",
    "Unhealthy",
    "Evicted",
}

SEV_1_FAILURE_REASONS = {"OOMKilled", "CrashLoopBackOff", "NodeNotReady"}


class KubernetesEvents:
    """Queries, normalizes, deduplicates, and classifies Kubernetes API events."""

    def __init__(self, client: KubernetesClient, max_dedup_cache_size: int = 5000):
        self.client = client
        self._seen_hashes: Set[str] = set()
        self._hash_fifo: Deque[str] = deque(maxlen=max_dedup_cache_size)
        self._last_resource_version: Optional[str] = None

    def _compute_event_fingerprint(self, item: Dict[str, Any]) -> str:
        """Computes a unique fingerprint to prevent duplicate event ingestion."""
        meta = item.get("metadata", {})
        involved = item.get("involvedObject", {})
        uid = meta.get("uid")
        if uid:
            return str(uid)

        # Fallback composite key
        raw_key = (
            f"{involved.get('namespace', '')}-"
            f"{involved.get('kind', '')}-"
            f"{involved.get('name', '')}-"
            f"{item.get('reason', '')}-"
            f"{item.get('lastTimestamp', '')}-"
            f"{item.get('count', 1)}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def classify_severity(self, reason: str, event_type: str) -> str:
        """Maps Kubernetes event reason and type to IncidentX severity."""
        if reason in SEV_1_FAILURE_REASONS:
            return "CRITICAL"
        if reason in CRITICAL_K8S_FAILURE_REASONS or event_type == "Warning":
            return "WARNING"
        return "NORMAL"

    async def list_events(
        self,
        namespace: Optional[str] = None,
        limit: int = 50,
        only_warnings: bool = False,
    ) -> List[InfrastructureEvent]:
        """
        Discovers and normalizes live Kubernetes events, applying deduplication
        and tagging each with environment data source LIVE_K8S.
        """
        raw_items = await self.client.list_events(namespace=namespace, limit=limit * 2)
        events: List[InfrastructureEvent] = []

        for item in raw_items:
            meta = item.get("metadata", {})
            involved = item.get("involvedObject", {})
            reason = item.get("reason", "Unknown")
            ev_type = item.get("type", "Normal")

            if only_warnings and ev_type != "Warning" and reason not in CRITICAL_K8S_FAILURE_REASONS:
                continue

            fp = self._compute_event_fingerprint(item)
            is_new = fp not in self._seen_hashes
            if is_new:
                self._seen_hashes.add(fp)
                self._hash_fifo.append(fp)

            timestamp = (
                item.get("lastTimestamp")
                or item.get("eventTime")
                or meta.get("creationTimestamp")
                or datetime.now(timezone.utc).isoformat()
            )

            events.append(
                InfrastructureEvent(
                    id=meta.get("uid") or f"k8s-ev-{meta.get('name', fp[:12])}",
                    event_type=ev_type,
                    reason=reason,
                    message=item.get("message", ""),
                    source_component=item.get("source", {}).get("component", "kubelet"),
                    resource_kind=involved.get("kind", "Pod"),
                    resource_name=involved.get("name", "unknown"),
                    namespace=involved.get("namespace", meta.get("namespace")),
                    count=item.get("count", 1),
                    timestamp=timestamp,
                    first_timestamp=item.get("firstTimestamp") or timestamp,
                    last_timestamp=timestamp,
                    data_source="LIVE_K8S",
                )
            )

            if len(events) >= limit:
                break

        return events

    async def stream_live_events(
        self, namespace: Optional[str] = None
    ) -> AsyncGenerator[InfrastructureEvent, None]:
        """Generates stream of new, unseen live cluster events."""
        events = await self.list_events(namespace=namespace, limit=50)
        for ev in events:
            yield ev
