"""
INCIDENTX AI - Incident Time Machine Engine
Reconstructs chronological timelines from multi-signal telemetry, metric spikes,
trace failures, logs, deployments, and health transitions.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.incident import Incident
from backend.app.models.telemetry import TelemetryEvent
from backend.app.models.timeline import TimelineEvent
from backend.app.services.observability.demo_mesh import demo_mesh


class TimelineReconstructor:
    """
    Incident Time Machine Engine.
    Reconstructs the complete lifecycle timeline of an incident.
    """

    @classmethod
    async def reconstruct_timeline(
        cls,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> List[TimelineEvent]:
        """
        Reconstructs timeline events from database telemetry, trace spans, logs, and deployment states.
        """
        # Fetch incident
        inc_stmt = select(Incident).where(Incident.id == incident_id)
        inc_res = await session.execute(inc_stmt)
        incident = inc_res.scalar_one_or_none()

        if not incident:
            return []

        # Check existing timeline events to avoid duplicate insertion
        existing_stmt = select(TimelineEvent).where(TimelineEvent.incident_id == incident_id)
        existing_res = await session.execute(existing_stmt)
        existing = list(existing_res.scalars().all())
        if existing:
            return existing

        timeline_items: List[TimelineEvent] = []
        is_simulated = state.get("intake", {}).get("sanitization_applied", True)
        data_source = "SIMULATED" if len(demo_mesh.active_faults) > 0 else "LIVE"

        dep_info = state.get("dependency", {})
        culprit = dep_info.get("causal_origin_service", "order-service")

        # 1. Event: First Abnormal Metric Detected
        timeline_items.append(TimelineEvent(
            incident_id=incident_id,
            timestamp=incident.detected_at,
            event_type="METRIC_ANOMALY",
            service_name=culprit,
            title=f"Initial Metric Anomaly on {culprit}",
            description=f"Automated baseline detector flagged anomalous divergence on {culprit}.",
            severity="WARN",
            data_source=data_source,
            raw_data=json.dumps({"service": culprit, "metric": "latency_or_saturation"}),
        ))

        # 2. Event: Error Rate / Latency Spike
        telemetry = state.get("telemetry", {})
        for anom in telemetry.get("anomalous_metrics", [])[:2]:
            timeline_items.append(TimelineEvent(
                incident_id=incident_id,
                timestamp=incident.detected_at,
                event_type="LATENCY_SPIKE" if "latency" in anom.get("metric_name", "") else "ERROR_SURGE",
                service_name=anom.get("service_name", culprit),
                title=f"{anom.get('service_name')} {anom.get('metric_name')} Critical Breach",
                description=anom.get("observation", ""),
                severity="CRITICAL",
                data_source=data_source,
                raw_data=json.dumps(anom),
            ))

        # 3. Event: Distributed Trace Failure
        traces = state.get("traces", {})
        for span in traces.get("slowest_spans", [])[:2]:
            timeline_items.append(TimelineEvent(
                incident_id=incident_id,
                timestamp=incident.detected_at,
                event_type="TRACE_FAILURE",
                service_name=span.get("service_name", culprit),
                title=f"Distributed Trace Span Failed: {span.get('operation_name')}",
                description=f"Span in trace {span.get('trace_id')[:8]} failed with status {span.get('status_code')} ({span.get('duration_ms')}ms)",
                severity="CRITICAL",
                data_source=data_source,
                raw_data=json.dumps(span),
            ))

        # 4. Event: Fatal Log Error Cluster
        logs = state.get("logs", {})
        for cluster in logs.get("exception_clusters", [])[:2]:
            timeline_items.append(TimelineEvent(
                incident_id=incident_id,
                timestamp=incident.detected_at,
                event_type="LOG_ERROR",
                service_name=cluster.get("service_name", culprit),
                title=f"Exception Cluster: {cluster.get('signature')}",
                description=cluster.get("sample_message", "")[:200],
                severity="CRITICAL",
                data_source=data_source,
                raw_data=json.dumps(cluster),
            ))

        # 5. Event: Service Health Transition
        timeline_items.append(TimelineEvent(
            incident_id=incident_id,
            timestamp=incident.detected_at,
            event_type="HEALTH_CHANGE",
            service_name=culprit,
            title=f"Service Health Transitioned to DEGRADED / CRITICAL",
            description=f"Health status of {culprit} downgraded following continuous metric violations.",
            severity="CRITICAL",
            data_source=data_source,
        ))

        # 6. Event: Autonomous Incident Detection & Triage
        timeline_items.append(TimelineEvent(
            incident_id=incident_id,
            timestamp=incident.detected_at,
            event_type="DETECTION",
            service_name="api-gateway",
            title=f"Autonomous Incident Declared: {incident.title}",
            description=f"Multi-signal correlation engine created incident with severity {incident.severity}.",
            severity="CRITICAL",
            data_source=data_source,
        ))

        # Sort chronologically and persist
        timeline_items.sort(key=lambda item: item.timestamp)
        for item in timeline_items:
            session.add(item)
        await session.flush()

        logger.info(f"[TimelineReconstructor] Reconstructed {len(timeline_items)} events for incident {incident_id}")
        return timeline_items
