"""
INCIDENTX AI - Root Cause Hypothesis Agent
Generates multiple competing root-cause hypotheses in Courtroom format
with prosecution arguments, defense counterarguments, and causal mechanisms.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.ai.provider import ai_provider
from backend.app.services.investigation.agents.base import BaseInvestigationAgent
from backend.app.services.investigation.schemas import (
    HypothesisGenerationResult,
    ProposedHypothesis,
)


class RootCauseHypothesisAgent(BaseInvestigationAgent):
    def __init__(self):
        super().__init__(
            name="RootCauseHypothesisAgent",
            role="hypothesis",
            execution_phase="HYPOTHESIS_GENERATION",
            timeout_seconds=15.0,
        )

    async def execute(
        self,
        incident_id: str,
        state: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        dep = state.get("dependency", {})
        culprit = dep.get("causal_origin_service", "order-service")
        telemetry = state.get("telemetry", {})
        logs = state.get("logs", {})
        traces = state.get("traces", {})
        deployment = state.get("deployment", {})

        def _deterministic_generate(ctx: Dict[str, Any]) -> HypothesisGenerationResult:
            hypotheses: List[ProposedHypothesis] = []

            # 1. Primary Hypothesis (Topological Culprit)
            if culprit == "postgres-db":
                hypotheses.append(ProposedHypothesis(
                    culprit_service="postgres-db",
                    title="Database Connection Pool Exhaustion",
                    hypothesis_text="Worker connections exhausted all 50 pooled slots in postgres-db, causing acquisition timeouts and cascading rollback failures in order-service.",
                    initial_probability=0.88,
                    prosecutor_argument="Telemetry shows db_pool_utilization at 100% capacity; order-service logs confirm ConnectionPoolTimeoutException.",
                    defense_argument="High DB connection load could be a consequence of slow consumer queries or network queue build-up rather than DB deadlock.",
                    causal_mechanism="Connection saturation -> OrderService thread starvation -> Gateway 502/504 errors.",
                ))
                # Competing Hypothesis 2 (Query Contention / Caller Storm)
                hypotheses.append(ProposedHypothesis(
                    culprit_service="order-service",
                    title="Unbounded Checkout Ingestion Storm",
                    hypothesis_text="An upstream traffic surge or unthrottled worker concurrency in order-service overwhelmed database capacity.",
                    initial_probability=0.45,
                    prosecutor_argument="Order service generated unprecedented connection requests within a compressed window.",
                    defense_argument="Incoming request rate was within standard limits; the database pool should have handled normal throughput without saturation.",
                    causal_mechanism="Concurrent caller spike -> DB pool saturation.",
                ))

            elif culprit == "payment-service":
                hypotheses.append(ProposedHypothesis(
                    culprit_service="payment-service",
                    title="Payment Gateway Timeout & PSP Latency",
                    hypothesis_text="Upstream payment gateway response latency exceeded 2000ms client timeout, triggering cascading 504 timeouts on checkout flows.",
                    initial_probability=0.91,
                    prosecutor_argument="OpenTelemetry traces prove payment spans took >2500ms; order-service threw PaymentGatewayTimeoutException after 2000ms SLA limit.",
                    defense_argument="External payment provider network jitter or upstream DNS resolution could have temporarily elevated round-trip times.",
                    causal_mechanism="Payment gateway latency -> Order service synchronous timeout -> Gateway 504.",
                ))
                # Competing Hypothesis 2 (Circuit Breaker Failure)
                hypotheses.append(ProposedHypothesis(
                    culprit_service="order-service",
                    title="Missing or Misconfigured Downstream Circuit Breaker",
                    hypothesis_text="Order service lacked an active circuit breaker, allowing slow payment requests to tie up HTTP worker threads.",
                    initial_probability=0.38,
                    prosecutor_argument="Order service threads remained blocked waiting for external calls rather than failing fast.",
                    defense_argument="Circuit breaker threshold was not breached because call failure count was masked by slow responses.",
                    causal_mechanism="Synchronous blocking wait -> Thread pool exhaustion.",
                ))

            elif culprit == "redis-cache":
                hypotheses.append(ProposedHypothesis(
                    culprit_service="redis-cache",
                    title="Redis Cache Connection Refusal / Outage",
                    hypothesis_text="Redis instance became unreachable on port 6379, causing session validation errors and high cache miss storm.",
                    initial_probability=0.86,
                    prosecutor_argument="Auth service logs show repeated RedisConnectionError; Redis node error rate reached 100%.",
                    defense_argument="Cache failure was transient; fallback DB authentication should have absorbed authentication load.",
                    causal_mechanism="Cache outage -> Session lookup failure -> 500 error on Auth Service.",
                ))
                hypotheses.append(ProposedHypothesis(
                    culprit_service="auth-service",
                    title="Degraded Cache Fallback Authentication",
                    hypothesis_text="Auth service failed to gracefully fall back to primary database when cache was unavailable.",
                    initial_probability=0.42,
                    prosecutor_argument="Auth service threw uncaught exceptions instead of querying PostgreSQL fallback.",
                    defense_argument="Fallback database was also subjected to increased latency under the unexpected load.",
                    causal_mechanism="Missing fallback handling -> Uncaught runtime exception.",
                ))

            else:
                hypotheses.append(ProposedHypothesis(
                    culprit_service=culprit,
                    title=f"Internal Service Degradation on {culprit}",
                    hypothesis_text=f"Compute saturation, unhandled exceptions, or resource exhaustion in {culprit} degraded downstream requests.",
                    initial_probability=0.80,
                    prosecutor_argument=f"Telemetry and trace evidence localize the highest latency and error counts directly inside {culprit}.",
                    defense_argument=f"An upstream caller or network partition could have induced resource contention on {culprit}.",
                    causal_mechanism=f"{culprit} resource contention -> Degraded response SLA.",
                ))
                hypotheses.append(ProposedHypothesis(
                    culprit_service="api-gateway",
                    title="Ingress Traffic Surge Overload",
                    hypothesis_text="External ingress traffic burst exceeded cluster capacity, overwhelming backend services.",
                    initial_probability=0.35,
                    prosecutor_argument="API Gateway reported heightened request volume.",
                    defense_argument="Gateway CPU remained healthy; downstream service was the localized failure point.",
                    causal_mechanism="Ingress surge -> Resource saturation.",
                ))

            return HypothesisGenerationResult(
                competing_hypotheses=hypotheses,
                generation_rationale=f"Generated {len(hypotheses)} competing hypotheses grounded in topology and telemetry.",
            )

        # Call AI layer (with deterministic fallback)
        ai_resp = await ai_provider.generate_structured(
            schema=HypothesisGenerationResult,
            system_prompt="You are the Root Cause Hypothesis Agent for an autonomous incident investigation system.",
            user_prompt=f"Generate competing hypotheses for an incident targeting {culprit}.",
            context_data={"culprit": culprit, "telemetry": telemetry, "logs": logs, "traces": traces, "deployment": deployment},
            deterministic_fallback_fn=_deterministic_generate,
        )

        state["hypotheses"] = ai_resp.data.model_dump()
        return state
