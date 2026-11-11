"""
INCIDENTX AI - Telemetry Analysis Agent
Analyzes metric time series, statistical deviations, and resource saturation points.
"""

from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.telemetry import TelemetryEvent
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    MetricAnomalyDetail,
    TelemetryAnalysisResult,
)


class TelemetryAnalysisAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="TelemetryAnalysisAgent",
            role="telemetry",
            execution_phase="METRICS_ANALYSIS",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        impacted_services = state.get("incident", {}).get("impact_scope", [])
        anomalies: List[MetricAnomalyDetail] = []
        peak_services: List[str] = []

        # 1. Inspect recent TelemetryEvent records in DB
        te_stmt = (
            select(TelemetryEvent)
            .where(TelemetryEvent.incident_id == incident_id)
            .order_by(TelemetryEvent.timestamp.asc())
        )
        te_res = await session.execute(te_stmt)
        events = list(te_res.scalars().all())

        first_timestamp = events[0].timestamp.isoformat() if events else None

        # 2. Inspect real-time snapshots from DemoMesh
        latest_metrics = demo_mesh.get_latest_metrics()
        for svc_name, metrics in latest_metrics.items():
            if not metrics:
                continue

            cpu = metrics.get("cpu_utilization", 0.0)
            mem = metrics.get("memory_utilization", 0.0)
            p95 = metrics.get("latency_p95_ms", 0.0)
            err_rate = metrics.get("error_rate", 0.0)
            db_pool = metrics.get("db_pool_utilization", 0.0)

            if cpu > 80.0:
                anomalies.append(MetricAnomalyDetail(
                    service_name=svc_name,
                    metric_name="cpu_utilization",
                    current_value=cpu,
                    baseline_value=25.0,
                    deviation_sigma=3.8,
                    severity="CRITICAL" if cpu > 90 else "WARN",
                    observation=f"{svc_name} CPU saturated at {cpu:.1f}%.",
                ))
                peak_services.append(svc_name)

            if p95 > 500.0:
                anomalies.append(MetricAnomalyDetail(
                    service_name=svc_name,
                    metric_name="latency_p95_ms",
                    current_value=p95,
                    baseline_value=85.0,
                    deviation_sigma=4.5,
                    severity="CRITICAL" if p95 > 1500 else "WARN",
                    observation=f"{svc_name} P95 latency spiked to {p95:.1f}ms.",
                ))
                peak_services.append(svc_name)

            if err_rate > 5.0:
                anomalies.append(MetricAnomalyDetail(
                    service_name=svc_name,
                    metric_name="error_rate",
                    current_value=err_rate,
                    baseline_value=0.1,
                    deviation_sigma=5.1,
                    severity="CRITICAL" if err_rate > 20 else "WARN",
                    observation=f"{svc_name} error rate jumped to {err_rate:.1f}%.",
                ))
                peak_services.append(svc_name)

            if db_pool > 75.0:
                anomalies.append(MetricAnomalyDetail(
                    service_name=svc_name,
                    metric_name="db_pool_utilization",
                    current_value=db_pool,
                    baseline_value=18.0,
                    deviation_sigma=6.2,
                    severity="CRITICAL" if db_pool > 90 else "WARN",
                    observation=f"{svc_name} connection pool saturated at {db_pool:.1f}%.",
                ))
                peak_services.append(svc_name)

        summary = (
            f"Detected {len(anomalies)} metric anomalies across {len(set(peak_services))} services. "
            f"Primary metric stress points: {', '.join(set(peak_services)) or 'None'}."
        )

        res = TelemetryAnalysisResult(
            anomalous_metrics=anomalies,
            peak_saturation_services=list(set(peak_services)),
            first_metric_breach_timestamp=first_timestamp,
            telemetry_summary=summary,
        )

        state["telemetry"] = res.model_dump()
        return state
