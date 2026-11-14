"""
INCIDENTX AI - OpenTelemetry Trace Collector & Buffer (Phase 8.3)
Ingests and buffers distributed traces adhering to OpenTelemetry OTLP/HTTP JSON standards.
Extracts Kubernetes resource provenance, microservice context, and correlates with active incidents.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import math

from backend.app.core.config import settings
from backend.app.infrastructure.core.infrastructure_models import (
    OpenTelemetrySpan,
    OpenTelemetryTrace,
)


def _parse_otlp_value(val_obj: Any) -> Any:
    """Extract primitive value from OTLP attribute object (stringValue, intValue, etc.)."""
    if not isinstance(val_obj, dict):
        return val_obj
    if "stringValue" in val_obj:
        return val_obj["stringValue"]
    if "intValue" in val_obj:
        try:
            return int(val_obj["intValue"])
        except (ValueError, TypeError):
            return val_obj["intValue"]
    if "doubleValue" in val_obj:
        try:
            return float(val_obj["doubleValue"])
        except (ValueError, TypeError):
            return val_obj["doubleValue"]
    if "boolValue" in val_obj:
        return bool(val_obj["boolValue"])
    if "arrayValue" in val_obj:
        values = val_obj["arrayValue"].get("values", [])
        return [_parse_otlp_value(v) for v in values]
    if "kvlistValue" in val_obj:
        values = val_obj["kvlistValue"].get("values", [])
        return {item.get("key"): _parse_otlp_value(item.get("value")) for item in values}
    return str(val_obj)


def _nano_to_iso(nano_or_iso: Any) -> str:
    """Convert unix nanoseconds or existing ISO string to UTC ISO-8601 string."""
    if isinstance(nano_or_iso, str) and ("T" in nano_or_iso or "-" in nano_or_iso):
        return nano_or_iso
    try:
        val = int(nano_or_iso)
        # If timestamp is in nanoseconds (> 1e16), divide by 1e9
        if val > 1_000_000_000_000_000:
            sec = val / 1_000_000_000.0
        # If milliseconds (> 1e11), divide by 1e3
        elif val > 100_000_000_000:
            sec = val / 1_000.0
        else:
            sec = float(val)
        return datetime.fromtimestamp(sec, tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _compute_duration_ms(start_val: Any, end_val: Any) -> float:
    """Calculate duration in milliseconds between start and end timestamps."""
    try:
        s_int = int(start_val)
        e_int = int(end_val)
        diff = max(0, e_int - s_int)
        if s_int > 1_000_000_000_000_000:  # nanoseconds
            return round(diff / 1_000_000.0, 3)
        elif s_int > 100_000_000_000:  # milliseconds
            return round(float(diff), 3)
        else:  # seconds
            return round(diff * 1000.0, 3)
    except Exception:
        # Try parsing as ISO strings
        try:
            s_dt = datetime.fromisoformat(str(start_val).replace("Z", "+00:00"))
            e_dt = datetime.fromisoformat(str(end_val).replace("Z", "+00:00"))
            delta = (e_dt - s_dt).total_seconds()
            return round(max(0.0, delta * 1000.0), 3)
        except Exception:
            return 0.0


class OpenTelemetryCollector:
    """
    In-memory FIFO buffer and ingestion processor for OpenTelemetry traces.
    """

    def __init__(self, max_buffer_size: Optional[int] = None):
        self.max_buffer_size = max_buffer_size or getattr(settings, "OTEL_MAX_BUFFERED_TRACES", 500)
        # Map of trace_id -> OpenTelemetryTrace
        self._traces: Dict[str, OpenTelemetryTrace] = {}
        self._trace_order: deque = deque(maxlen=self.max_buffer_size)
        self.total_ingested_spans: int = 0
        self.total_ingested_traces: int = 0

    def ingest_otlp_payload(self, payload: Dict[str, Any]) -> List[str]:
        """
        Process standard OTLP JSON payload containing resourceSpans.
        Returns list of ingested trace_ids.
        """
        resource_spans = payload.get("resourceSpans", [])
        if not resource_spans and "spans" in payload:
            # Flattened or custom format support
            return self._ingest_flat_spans(payload.get("spans", []))

        ingested_ids: List[str] = []

        for r_span in resource_spans:
            # Extract resource attributes
            resource_attrs: Dict[str, Any] = {}
            for attr in r_span.get("resource", {}).get("attributes", []):
                k = attr.get("key")
                if k:
                    resource_attrs[k] = _parse_otlp_value(attr.get("value"))

            default_service = resource_attrs.get("service.name", "unknown_service")
            k8s_ns = resource_attrs.get("k8s.namespace.name")
            k8s_pod = resource_attrs.get("k8s.pod.name")
            k8s_deployment = resource_attrs.get("k8s.deployment.name")

            for scope_span in r_span.get("scopeSpans", []):
                for raw_span in scope_span.get("spans", []):
                    span = self._parse_single_span(
                        raw_span=raw_span,
                        resource_attrs=resource_attrs,
                        default_service=default_service,
                        k8s_ns=k8s_ns,
                        k8s_pod=k8s_pod,
                        k8s_deployment=k8s_deployment,
                    )
                    self._add_span_to_trace(span)
                    if span.trace_id not in ingested_ids:
                        ingested_ids.append(span.trace_id)

        return ingested_ids

    def _ingest_flat_spans(self, spans_data: List[Dict[str, Any]]) -> List[str]:
        ingested_ids: List[str] = []
        for raw in spans_data:
            span = self._parse_single_span(raw_span=raw, resource_attrs={}, default_service="unknown_service")
            self._add_span_to_trace(span)
            if span.trace_id not in ingested_ids:
                ingested_ids.append(span.trace_id)
        return ingested_ids

    def _parse_single_span(
        self,
        raw_span: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        default_service: str = "unknown_service",
        k8s_ns: Optional[str] = None,
        k8s_pod: Optional[str] = None,
        k8s_deployment: Optional[str] = None,
    ) -> OpenTelemetrySpan:
        trace_id = raw_span.get("traceId") or raw_span.get("trace_id") or "unknown_trace"
        span_id = raw_span.get("spanId") or raw_span.get("span_id") or "unknown_span"
        parent_id = raw_span.get("parentSpanId") or raw_span.get("parent_span_id") or None
        name = raw_span.get("name", "unnamed_operation")

        # Span attributes
        span_attrs: Dict[str, Any] = dict(resource_attrs)
        raw_attrs = raw_span.get("attributes", [])
        if isinstance(raw_attrs, list):
            for a in raw_attrs:
                k = a.get("key")
                if k:
                    span_attrs[k] = _parse_otlp_value(a.get("value"))
        elif isinstance(raw_attrs, dict):
            span_attrs.update(raw_attrs)

        # Top-level direct keys or attributes
        for k in ("service.name", "service_name", "incident_id", "incident.id", "k8s.pod.name", "k8s.namespace.name"):
            if k in raw_span and k not in span_attrs:
                span_attrs[k] = raw_span[k]

        svc = raw_span.get("service_name") or raw_span.get("service.name") or span_attrs.get("service.name") or span_attrs.get("service_name") or default_service
        ns = raw_span.get("k8s.namespace.name") or span_attrs.get("k8s.namespace.name", k8s_ns)
        pod = raw_span.get("k8s.pod.name") or span_attrs.get("k8s.pod.name", k8s_pod)
        deployment = raw_span.get("k8s.deployment.name") or span_attrs.get("k8s.deployment.name", k8s_deployment)
        incident_id = raw_span.get("incident_id") or raw_span.get("incident.id") or span_attrs.get("incident_id") or span_attrs.get("incident.id")

        # Timestamps and duration
        start_raw = raw_span.get("startTimeUnixNano") or raw_span.get("start_time", 0)
        end_raw = raw_span.get("endTimeUnixNano") or raw_span.get("end_time", 0)
        start_iso = _nano_to_iso(start_raw)
        end_iso = _nano_to_iso(end_raw)
        duration_ms = _compute_duration_ms(start_raw, end_raw)
        if duration_ms == 0.0 and "duration_ms" in raw_span:
            duration_ms = float(raw_span["duration_ms"])

        # Status
        status_obj = raw_span.get("status", {})
        status_code = "OK"
        status_msg = None
        if isinstance(status_obj, dict):
            code_raw = status_obj.get("code")
            # 2 = STATUS_CODE_ERROR in OTLP
            if code_raw == 2 or code_raw == "ERROR" or code_raw == "STATUS_CODE_ERROR":
                status_code = "ERROR"
            elif code_raw == 1 or code_raw == "OK" or code_raw == "STATUS_CODE_OK":
                status_code = "OK"
            else:
                status_code = "UNSET"
            status_msg = status_obj.get("message")
        elif isinstance(status_obj, str):
            status_code = "ERROR" if status_obj.upper() == "ERROR" else "OK"

        # Check HTTP status code in attributes
        http_status = span_attrs.get("http.status_code") or span_attrs.get("http.response.status_code")
        if http_status and int(http_status) >= 500:
            status_code = "ERROR"
            if not status_msg:
                status_msg = f"HTTP {http_status} Server Error"

        is_error = status_code == "ERROR"

        return OpenTelemetrySpan(
            trace_id=str(trace_id),
            span_id=str(span_id),
            parent_span_id=str(parent_id) if parent_id else None,
            name=name,
            service_name=svc,
            kind=str(raw_span.get("kind", "SPAN_KIND_SERVER")),
            start_time_iso=start_iso,
            end_time_iso=end_iso,
            duration_ms=duration_ms,
            status_code=status_code,
            status_message=status_msg,
            attributes=span_attrs,
            events=raw_span.get("events", []),
            k8s_namespace=ns,
            k8s_pod_name=pod,
            k8s_deployment_name=deployment,
            incident_id=str(incident_id) if incident_id else None,
            is_error=is_error,
        )

    def _add_span_to_trace(self, span: OpenTelemetrySpan) -> None:
        self.total_ingested_spans += 1
        trace_id = span.trace_id

        if trace_id not in self._traces:
            # Enforce max buffer size
            if len(self._traces) >= self.max_buffer_size:
                oldest_id = self._trace_order.popleft()
                self._traces.pop(oldest_id, None)

            new_trace = OpenTelemetryTrace(
                trace_id=trace_id,
                root_service=span.service_name,
                root_operation=span.name,
                start_time_iso=span.start_time_iso,
                duration_ms=span.duration_ms,
                span_count=1,
                error_count=1 if span.is_error else 0,
                has_error=span.is_error,
                spans=[span],
                incident_id=span.incident_id,
            )
            self._traces[trace_id] = new_trace
            self._trace_order.append(trace_id)
            self.total_ingested_traces += 1
        else:
            trace = self._traces[trace_id]
            # Avoid duplicate span_id
            existing_idx = next((i for i, s in enumerate(trace.spans) if s.span_id == span.span_id), None)
            if existing_idx is not None:
                trace.spans[existing_idx] = span
            else:
                trace.spans.append(span)

            trace.span_count = len(trace.spans)
            trace.error_count = sum(1 for s in trace.spans if s.is_error)
            trace.has_error = trace.error_count > 0
            if span.incident_id and not trace.incident_id:
                trace.incident_id = span.incident_id

            # Update trace duration and start_time
            if trace.spans:
                trace.spans.sort(key=lambda s: s.start_time_iso)
                trace.start_time_iso = trace.spans[0].start_time_iso
                trace.duration_ms = max(s.duration_ms for s in trace.spans)
                # If root span without parent exists, update root operation
                root_span = next((s for s in trace.spans if not s.parent_span_id), trace.spans[0])
                trace.root_service = root_span.service_name
                trace.root_operation = root_span.name

    def get_trace(self, trace_id: str) -> Optional[OpenTelemetryTrace]:
        return self._traces.get(trace_id)

    def list_traces(
        self,
        service_name: Optional[str] = None,
        only_errors: bool = False,
        incident_id: Optional[str] = None,
        min_duration_ms: Optional[float] = None,
        limit: int = 50,
    ) -> List[OpenTelemetryTrace]:
        results: List[OpenTelemetryTrace] = []
        # Return newest first
        for t_id in reversed(self._trace_order):
            trace = self._traces.get(t_id)
            if not trace:
                continue
            if service_name and trace.root_service.lower() != service_name.lower():
                # Also check if any span matches
                if not any(s.service_name.lower() == service_name.lower() for s in trace.spans):
                    continue
            if only_errors and not trace.has_error:
                continue
            if incident_id and trace.incident_id != incident_id:
                continue
            if min_duration_ms is not None and trace.duration_ms < min_duration_ms:
                continue

            results.append(trace)
            if len(results) >= limit:
                break
        return results

    def clear(self) -> None:
        """Clear trace buffer."""
        self._traces.clear()
        self._trace_order.clear()


# Global singleton instance
otel_collector = OpenTelemetryCollector()
