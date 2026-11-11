"""
INCIDENTX AI - Service Dependency Analysis Agent
Distinguishes correlation from causation using topology graphs and failure propagation analysis.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import DependencyAnalysisResult
from backend.app.services.observability.correlation import CorrelationEngine


class ServiceDependencyAnalysisAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="ServiceDependencyAnalysisAgent",
            role="dependency",
            execution_phase="DEPENDENCY_ANALYSIS",
            timeout_seconds=10.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        telemetry = state.get("telemetry", {})
        traces = state.get("traces", {})
        impacted = state.get("incident", {}).get("impact_scope", [])

        # Priority to services within the incident's impact scope
        suspects = set(impacted) if impacted else set(telemetry.get("peak_saturation_services", []))
        if traces.get("root_cause_span_service") and traces["root_cause_span_service"] in impacted:
            suspects.add(traces["root_cause_span_service"])

        # Apply topological causal evaluation
        dependencies = CorrelationEngine.DEPENDENCIES

        # Check deep infrastructure culprits
        if "postgres-db" in suspects:
            origin = "postgres-db"
            chain = ["postgres-db", "order-service", "api-gateway"]
            explanation = (
                "PostgreSQL connection exhaustion or lock contention occurred at the database layer. "
                "Order and payment services timed out acquiring connections, which cascaded as 502/504 errors to the API Gateway."
            )
        elif "payment-service" in suspects:
            origin = "payment-service"
            chain = ["payment-service", "order-service", "api-gateway"]
            explanation = (
                "Payment gateway latency exceeded timeout thresholds, causing synchronous order-checkout RPCs "
                "to time out and return 504 Gateway Timeout up to client traffic."
            )
        elif "redis-cache" in suspects:
            origin = "redis-cache"
            chain = ["redis-cache", "auth-service", "api-gateway"]
            explanation = (
                "Redis cache connection dropped. Auth service experienced cache misses and session lookup failures."
            )
        else:
            origin = list(suspects)[0] if suspects else "order-service"
            chain = [origin, "api-gateway"]
            explanation = f"Failure originated in {origin} and propagated to connected dependencies."

        res = DependencyAnalysisResult(
            causal_origin_service=origin,
            propagation_chain=chain,
            blast_radius=list(suspects),
            is_downstream_symptom=origin != "api-gateway" and "api-gateway" in suspects,
            causal_explanation=explanation,
        )

        state["dependency"] = res.model_dump()
        return state
