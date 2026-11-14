"""
INCIDENTX AI - OpenTelemetry Trace Investigator (Phase 8.3)
Performs deep structural analysis on distributed traces:
- Critical-path & bottleneck span detection
- Error root-cause propagation
- Parent-child tree hierarchy & waterfall visualization mapping
- Service caller-callee dependency inference
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.infrastructure.core.infrastructure_models import (
    OpenTelemetrySpan,
    OpenTelemetryTrace,
)
from backend.app.services.observability.opentelemetry.trace_collector import otel_collector


class TraceInvestigator:
    """
    Diagnostic engine analyzing distributed trace graphs for latency bottlenecks and failures.
    """

    def analyze_trace(self, trace: OpenTelemetryTrace) -> Dict[str, Any]:
        """
        Analyze a single trace: identifies bottlenecks, errors, and tree hierarchy.
        """
        if not trace.spans:
            return {
                "trace_id": trace.trace_id,
                "status": "EMPTY",
                "bottleneck_span": None,
                "error_spans": [],
                "tree": [],
                "dependency_edges": [],
            }

        # 1. Detect Bottleneck Span (span with maximum duration)
        sorted_by_duration = sorted(trace.spans, key=lambda s: s.duration_ms, reverse=True)
        bottleneck_span = sorted_by_duration[0] if sorted_by_duration else None
        if bottleneck_span and bottleneck_span.duration_ms > 0:
            bottleneck_span.is_bottleneck = True
            trace.bottleneck_span_id = bottleneck_span.span_id

        # 2. Extract Error Spans
        error_spans = [s for s in trace.spans if s.is_error]

        # 3. Construct Parent-Child Hierarchy & Call Tree
        span_map: Dict[str, OpenTelemetrySpan] = {s.span_id: s for s in trace.spans}
        children_map: Dict[str, List[str]] = {}
        root_spans: List[OpenTelemetrySpan] = []

        for s in trace.spans:
            if not s.parent_span_id or s.parent_span_id not in span_map:
                root_spans.append(s)
            else:
                children_map.setdefault(s.parent_span_id, []).append(s.span_id)

        # Build chronological hierarchical tree with depth and relative start offset
        tree: List[Dict[str, Any]] = []
        if root_spans:
            # Baseline start timestamp for offset calculation
            earliest_iso = min(s.start_time_iso for s in trace.spans)

            def traverse(span: OpenTelemetrySpan, depth: int):
                tree.append({
                    "span_id": span.span_id,
                    "parent_span_id": span.parent_span_id,
                    "name": span.name,
                    "service_name": span.service_name,
                    "kind": span.kind,
                    "duration_ms": span.duration_ms,
                    "status_code": span.status_code,
                    "status_message": span.status_message,
                    "depth": depth,
                    "is_bottleneck": span.is_bottleneck,
                    "is_error": span.is_error,
                    "k8s_pod": span.k8s_pod_name,
                    "k8s_namespace": span.k8s_namespace,
                    "attributes": span.attributes,
                })
                child_ids = children_map.get(span.span_id, [])
                # Sort children chronologically
                children = [span_map[cid] for cid in child_ids if cid in span_map]
                children.sort(key=lambda c: c.start_time_iso)
                for child in children:
                    traverse(child, depth + 1)

            for r in sorted(root_spans, key=lambda s: s.start_time_iso):
                traverse(r, 0)
        else:
            # Fallback flat tree
            for s in trace.spans:
                tree.append({
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "name": s.name,
                    "service_name": s.service_name,
                    "duration_ms": s.duration_ms,
                    "status_code": s.status_code,
                    "depth": 0,
                    "is_bottleneck": s.is_bottleneck,
                    "is_error": s.is_error,
                })

        # 4. Infer Caller -> Callee Service Dependency Edges
        dependency_edges: List[Dict[str, str]] = []
        seen_edges: Set[Tuple[str, str]] = set()

        for s in trace.spans:
            if s.parent_span_id and s.parent_span_id in span_map:
                parent = span_map[s.parent_span_id]
                if parent.service_name != s.service_name:
                    edge = (parent.service_name, s.service_name)
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        dependency_edges.append({
                            "source_service": parent.service_name,
                            "target_service": s.service_name,
                            "operation": s.name,
                            "has_error": s.is_error,
                        })

        return {
            "trace_id": trace.trace_id,
            "root_service": trace.root_service,
            "root_operation": trace.root_operation,
            "duration_ms": trace.duration_ms,
            "span_count": trace.span_count,
            "error_count": len(error_spans),
            "has_error": len(error_spans) > 0,
            "bottleneck_span": bottleneck_span.model_dump() if bottleneck_span else None,
            "error_spans": [s.model_dump() for s in error_spans],
            "tree": tree,
            "dependency_edges": dependency_edges,
        }

    def correlate_incident_traces(
        self,
        incident_id: str,
        impacted_services: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Discover traces correlated with an incident ID or its impacted microservices.
        """
        # First query by explicit incident_id tag
        traces = otel_collector.list_traces(incident_id=incident_id, limit=limit)

        # Fallback to querying by impacted services
        if not traces and impacted_services:
            for svc in impacted_services:
                traces.extend(otel_collector.list_traces(service_name=svc, limit=10))

        # Deduplicate
        seen_ids = set()
        unique_traces: List[OpenTelemetryTrace] = []
        for t in traces:
            if t.trace_id not in seen_ids:
                seen_ids.add(t.trace_id)
                unique_traces.append(t)

        analyzed_traces = [self.analyze_trace(t) for t in unique_traces[:limit]]
        failed_count = sum(1 for a in analyzed_traces if a.get("has_error"))
        culprit_services: Dict[str, int] = {}
        for a in analyzed_traces:
            for err in a.get("error_spans", []):
                svc = err.get("service_name")
                if svc:
                    culprit_services[svc] = culprit_services.get(svc, 0) + 1

        top_culprit = max(culprit_services, key=culprit_services.get) if culprit_services else None

        return {
            "incident_id": incident_id,
            "correlated_traces_count": len(analyzed_traces),
            "failed_traces_count": failed_count,
            "top_culprit_service": top_culprit,
            "traces": analyzed_traces,
        }


# Global singleton instance
trace_investigator = TraceInvestigator()
