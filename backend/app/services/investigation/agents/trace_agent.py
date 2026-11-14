"""
INCIDENTX AI - Trace Analysis Agent
Inspects OpenTelemetry distributed traces, span waterfalls, and caller-callee latency bottlenecks.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    TraceAnalysisResult,
    TraceSpanFailure,
)
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.opentelemetry.trace_collector import otel_collector
from backend.app.services.observability.opentelemetry.trace_investigator import trace_investigator


class TraceAnalysisAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="TraceAnalysisAgent",
            role="trace",
            execution_phase="TRACE_ANALYSIS",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        failures: List[TraceSpanFailure] = []
        culprit_spans: Dict[str, int] = {}
        total_traces_examined = 0
        failed_traces_count = 0

        # 1. First check OpenTelemetry live trace collector
        otel_traces = otel_collector.list_traces(incident_id=incident_id, limit=30)
        if not otel_traces:
            otel_traces = otel_collector.list_traces(only_errors=True, limit=30)

        if otel_traces:
            total_traces_examined = len(otel_traces)
            failed_traces_count = sum(1 for t in otel_traces if t.has_error)
            for t in otel_traces:
                analysis = trace_investigator.analyze_trace(t)
                for err in analysis.get("error_spans", []):
                    failures.append(TraceSpanFailure(
                        trace_id=t.trace_id,
                        span_id=err.get("span_id", ""),
                        service_name=err.get("service_name", "unknown"),
                        operation_name=err.get("name", ""),
                        duration_ms=float(err.get("duration_ms", 0.0)),
                        status_code=500 if err.get("is_error") else 200,
                        error_message=err.get("status_message"),
                    ))
                    svc = err.get("service_name", "unknown")
                    culprit_spans[svc] = culprit_spans.get(svc, 0) + 1

                # If bottleneck span took > 500ms, also flag it
                bn = analysis.get("bottleneck_span")
                if bn and bn.get("duration_ms", 0) > 500.0:
                    failures.append(TraceSpanFailure(
                        trace_id=t.trace_id,
                        span_id=bn.get("span_id", ""),
                        service_name=bn.get("service_name", "unknown"),
                        operation_name=bn.get("name", ""),
                        duration_ms=float(bn.get("duration_ms", 0.0)),
                        status_code=200,
                        error_message=f"Critical path bottleneck ({bn.get('duration_ms'):.1f}ms)",
                    ))
                    svc = bn.get("service_name", "unknown")
                    culprit_spans[svc] = culprit_spans.get(svc, 0) + 1

        # 2. Fallback to DemoMesh simulation traces if no live OTel traces available
        if not failures:
            recent_traces = demo_mesh.get_traces(limit=60, only_errors=True)
            if not recent_traces:
                recent_traces = demo_mesh.get_traces(limit=20)
            total_traces_examined = len(recent_traces)
            failed_traces_count = len([t for t in recent_traces if t.get("has_error")])

            for t in recent_traces:
                for s in t.get("spans", []):
                    status = s.get("status", "OK")
                    duration = float(s.get("duration_ms", 0.0))
                    svc = s.get("service_name", "unknown")
                    code = int(s.get("status_code", 200))

                    if status == "ERROR" or code >= 500 or duration > 1000.0:
                        failures.append(TraceSpanFailure(
                            trace_id=t.get("trace_id", ""),
                            span_id=s.get("span_id", ""),
                            service_name=svc,
                            operation_name=s.get("name", ""),
                            duration_ms=duration,
                            status_code=code,
                            error_message=s.get("error_message"),
                        ))
                        culprit_spans[svc] = culprit_spans.get(svc, 0) + 1

        failures.sort(key=lambda f: f.duration_ms, reverse=True)
        root_service = max(culprit_spans, key=culprit_spans.get) if culprit_spans else None

        summary = (
            f"Examined {total_traces_examined} distributed traces across OTel and mesh. "
            f"Detected {len(failures)} failed or degraded spans. "
            f"Primary bottleneck service in traces: {root_service or 'None'}."
        )

        res = TraceAnalysisResult(
            failed_traces_count=failed_traces_count,
            slowest_spans=failures[:6],
            root_cause_span_service=root_service,
            waterfall_bottleneck_summary=summary,
        )

        state["traces"] = res.model_dump()
        return state
