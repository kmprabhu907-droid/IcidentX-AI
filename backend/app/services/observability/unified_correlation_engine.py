"""
INCIDENTX AI - Unified Telemetry Correlation Engine (Phase 8.3)
Aggregates, correlates, and normalizes heterogeneous telemetry streams into a single
chronological incident timeline with strict provenance tracking (SIMULATED vs LIVE_K8S).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.core.environment_manager import environment_manager
from backend.app.infrastructure.core.infrastructure_models import (
    EnvironmentMode,
    UnifiedTelemetryTimelineItem,
)
from backend.app.models.incident import Incident
from backend.app.models.telemetry import TelemetryEvent
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.opentelemetry.trace_collector import otel_collector


def _ensure_utc_iso(ts_val: Any) -> str:
    """Normalize any timestamp (int, float, datetime, string) into a UTC ISO-8601 string."""
    if isinstance(ts_val, datetime):
        if ts_val.tzinfo is None:
            ts_val = ts_val.replace(tzinfo=timezone.utc)
        return ts_val.astimezone(timezone.utc).isoformat()
    if isinstance(ts_val, (int, float)):
        # If timestamp is in milliseconds (> 1e11), divide by 1e3
        if ts_val > 100_000_000_000:
            ts_val = ts_val / 1000.0
        return datetime.fromtimestamp(ts_val, tz=timezone.utc).isoformat()
    if isinstance(ts_val, str):
        try:
            cleaned = ts_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return ts_val
    return datetime.now(timezone.utc).isoformat()


class UnifiedCorrelationEngine:
    """
    Synthesizes and correlates telemetry across Prometheus, OpenTelemetry,
    Kubernetes events, application logs, and incident lifecycle transitions.
    """

    async def build_incident_timeline(
        self,
        incident_id: str,
        session: Optional[AsyncSession] = None,
        limit: int = 100,
    ) -> List[UnifiedTelemetryTimelineItem]:
        """
        Assemble a comprehensive chronological timeline for an incident across all telemetry sources.
        """
        items: List[UnifiedTelemetryTimelineItem] = []
        incident_obj: Optional[Incident] = None

        # 1. Fetch Incident Record (if DB session provided)
        if session:
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await session.execute(stmt)
            incident_obj = res.scalar_one_or_none()

        if incident_obj:
            # Add Incident Creation milestone
            items.append(
                UnifiedTelemetryTimelineItem(
                    id=f"inc-create-{incident_obj.id}",
                    timestamp=_ensure_utc_iso(incident_obj.created_at),
                    source="INCIDENT",
                    category="INCIDENT_STATE",
                    severity=incident_obj.severity or "HIGH",
                    resource_name=incident_obj.title,
                    message=f"Incident '{incident_obj.title}' created (Status: {incident_obj.status})",
                    details={
                        "incident_id": incident_obj.id,
                        "status": incident_obj.status,
                        "severity": incident_obj.severity,
                        "impact_scope": incident_obj.impact_scope,
                    },
                    data_source="SIMULATED" if environment_manager.active_mode == EnvironmentMode.DEMOMESH else "LIVE_K8S",
                    incident_id=incident_id,
                )
            )

        # 2. Correlate OpenTelemetry Traces
        otel_traces = otel_collector.list_traces(incident_id=incident_id, limit=30)
        # If no traces explicitly tagged with incident_id, check by impacted service
        if not otel_traces and incident_obj and incident_obj.impact_scope:
            for svc in incident_obj.impact_scope:
                otel_traces.extend(otel_collector.list_traces(service_name=svc, limit=10))

        for trace in otel_traces:
            for span in trace.spans:
                if span.is_error or span.duration_ms > 500.0 or span.is_bottleneck:
                    sev = "CRITICAL" if span.is_error else ("HIGH" if span.duration_ms > 1000.0 else "WARN")
                    items.append(
                        UnifiedTelemetryTimelineItem(
                            id=f"otel-span-{span.span_id}",
                            timestamp=_ensure_utc_iso(span.start_time_iso),
                            source="OPENTELEMETRY",
                            category="TRACE_FAILURE" if span.is_error else "METRIC_ANOMALY",
                            severity=sev,
                            resource_name=f"{span.service_name}::{span.name}",
                            message=span.status_message or f"Span execution took {span.duration_ms:.1f}ms (Bottleneck: {span.is_bottleneck})",
                            details={
                                "trace_id": span.trace_id,
                                "span_id": span.span_id,
                                "duration_ms": span.duration_ms,
                                "status_code": span.status_code,
                                "k8s_pod": span.k8s_pod_name,
                                "k8s_namespace": span.k8s_namespace,
                            },
                            data_source="LIVE_K8S" if span.k8s_pod_name else "SIMULATED",
                            incident_id=incident_id,
                        )
                    )

        # 3. Correlate Infrastructure / Kubernetes Events
        active_adapter = environment_manager.get_active_adapter()
        try:
            infra_events = await active_adapter.get_infrastructure_events(limit=40)
            for evt in infra_events:
                # Filter events that match incident impacted resources or high severity
                evt_sev = "HIGH" if evt.event_type.upper() in ("WARNING", "ERROR", "CRITICAL") else "INFO"
                if evt.reason in ("OOMKilled", "CrashLoopBackOff", "FailedScheduling", "Unhealthy"):
                    evt_sev = "CRITICAL"

                items.append(
                    UnifiedTelemetryTimelineItem(
                        id=f"infra-evt-{evt.id}",
                        timestamp=_ensure_utc_iso(evt.timestamp),
                        source="KUBERNETES" if evt.data_source == "LIVE_K8S" else "DEMOMESH",
                        category="K8S_EVENT",
                        severity=evt_sev,
                        resource_name=f"{evt.resource_kind}/{evt.resource_name}",
                        message=f"[{evt.reason}] {evt.message}",
                        details={
                            "reason": evt.reason,
                            "component": evt.source_component,
                            "namespace": evt.namespace,
                            "count": evt.count,
                        },
                        data_source=evt.data_source,
                        incident_id=incident_id,
                    )
                )
        except Exception:
            pass

        # 4. Correlate DB Telemetry Events (TelemetryEvent records)
        if session:
            stmt = (
                select(TelemetryEvent)
                .where(TelemetryEvent.incident_id == incident_id)
                .order_by(TelemetryEvent.timestamp.asc())
                .limit(50)
            )
            te_res = await session.execute(stmt)
            for te in te_res.scalars().all():
                te_ds = getattr(te, "data_source", "SIMULATED")
                te_sigma = getattr(te, "deviation_sigma", None)
                te_svc = getattr(te, "service_name", None)
                if not te_svc:
                    te_svc = f"svc-{te.service_id[:8]}" if getattr(te, "service_id", None) else "cluster"
                items.append(
                    UnifiedTelemetryTimelineItem(
                        id=f"db-te-{te.id}",
                        timestamp=_ensure_utc_iso(te.timestamp),
                        source="DEMOMESH" if te_ds == "SIMULATED" else "PROMETHEUS",
                        category="METRIC_ANOMALY",
                        severity="WARN" if te_sigma and te_sigma > 3.0 else (te.severity or "INFO"),
                        resource_name=te_svc,
                        message=f"{te.metric_name or te.event_type} measured at {te.metric_value or 0.0}",
                        details={
                            "metric_name": te.metric_name,
                            "metric_value": te.metric_value,
                            "baseline": getattr(te, "baseline_value", None),
                            "deviation_sigma": te_sigma,
                        },
                        data_source=te_ds,
                        incident_id=incident_id,
                    )
                )

        # 5. Correlate DemoMesh active faults (if in DemoMesh mode)
        if environment_manager.active_mode == EnvironmentMode.DEMOMESH:
            for fault_id, fault in demo_mesh.active_faults.items():
                items.append(
                    UnifiedTelemetryTimelineItem(
                        id=f"demomesh-fault-{fault_id}",
                        timestamp=_ensure_utc_iso(fault.get("injected_at", datetime.now(timezone.utc))),
                        source="DEMOMESH",
                        category="METRIC_ANOMALY",
                        severity="CRITICAL",
                        resource_name=fault.get("service", "unknown"),
                        message=f"DemoMesh Fault Injected: {fault.get('fault_type')} (intensity {fault.get('intensity', 1.0)})",
                        details=fault,
                        data_source="SIMULATED",
                        incident_id=incident_id,
                    )
                )

        # Sort all items chronologically by UTC timestamp
        items.sort(key=lambda x: x.timestamp)
        return items[:limit]


# Global singleton instance
unified_correlation_engine = UnifiedCorrelationEngine()
