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
        recent_traces = demo_mesh.get_traces(limit=60, only_errors=True)
        if not recent_traces:
            recent_traces = demo_mesh.get_traces(limit=20)

        failures: List[TraceSpanFailure] = []
        culprit_spans: Dict[str, int] = {}

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
            f"Examined {len(recent_traces)} distributed traces. Detected {len(failures)} failed or degraded spans. "
            f"Primary bottleneck service in traces: {root_service or 'None'}."
        )

        res = TraceAnalysisResult(
            failed_traces_count=len([t for t in recent_traces if t.get("has_error")]),
            slowest_spans=failures[:6],
            root_cause_span_service=root_service,
            waterfall_bottleneck_summary=summary,
        )

        state["traces"] = res.model_dump()
        return state
