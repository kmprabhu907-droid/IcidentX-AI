"""
INCIDENTX AI - LangGraph Autonomous Reliability Intelligence Agent (Stage 5.8)
Synthesizes streaming telemetry, active anomalies, historical reliability memory,
post-remediation regressions, predictive exhaustion horizons, and SLO error budgets.
Produces auditable, explainable remediation recommendations with deterministic fallbacks.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import END, StateGraph

from backend.app.core.logging import logger
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.services.observability.anomaly import anomaly_service
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.regression.fingerprint import FingerprintBuilder
from backend.app.services.predictive import PredictiveReliabilityEngine
from backend.app.services.reliability_memory import ReliabilityMemoryEngine
from backend.app.services.slo import SLOIntelligenceEngine


class ReliabilityAgentState(TypedDict):
    """Execution state passed through the LangGraph reasoning loop."""
    service_name: str
    incident_id: Optional[str]
    telemetry_data: Dict[str, Any]
    active_anomalies: List[Dict[str, Any]]
    similar_memories: List[Dict[str, Any]]
    regressions: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    slo_reports: List[Dict[str, Any]]
    reasoning_trace: List[str]
    decision: Dict[str, Any]
    escalation_flag: bool
    timestamp: str


class LangGraphReliabilityAgent:
    """
    Autonomous multi-node reasoning graph powered by LangGraph.
    """

    _last_run_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def get_last_run(cls) -> Optional[Dict[str, Any]]:
        """Returns the cached result of the most recent agent assessment."""
        return cls._last_run_cache

    @classmethod
    async def assess(
        cls,
        service_name: Optional[str] = None,
        incident_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full 8-node LangGraph autonomous assessment loop.
        """
        target_service = service_name or "order-service"
        initial_state: ReliabilityAgentState = {
            "service_name": target_service,
            "incident_id": incident_id,
            "telemetry_data": {},
            "active_anomalies": [],
            "similar_memories": [],
            "regressions": [],
            "predictions": [],
            "slo_reports": [],
            "reasoning_trace": [],
            "decision": {},
            "escalation_flag": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Build LangGraph workflow
        workflow = StateGraph(ReliabilityAgentState)

        # Node 1: Telemetry
        async def telemetry_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            metrics = demo_mesh.get_latest_metrics().get(state["service_name"], {})
            trace = f"Gathered streaming telemetry for {state['service_name']}: CPU={metrics.get('cpu_utilization', 0):.1f}%, Mem={metrics.get('memory_utilization', 0):.1f}%, DB_Pool={metrics.get('db_pool_utilization', 0):.1f}%, ErrRate={metrics.get('error_rate', 0):.3f}."
            return {
                "telemetry_data": metrics,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 2: Anomaly Context
        async def anomaly_context_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            active_anoms = await anomaly_service.get_active_anomalies()
            service_anoms = [a for a in active_anoms if a.get("service_name") == state["service_name"]]
            trace = f"Retrieved {len(service_anoms)} active anomalies for {state['service_name']} (cluster total: {len(active_anoms)})."
            return {
                "active_anomalies": service_anoms,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 3: Memory Retrieval
        async def memory_retrieval_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            memories: List[Dict[str, Any]] = []
            if db:
                try:
                    # Construct search fingerprint from current telemetry
                    m = state["telemetry_data"]
                    anoms: Dict[str, float] = {}
                    if m.get("error_rate", 0) > 0.05:
                        anoms["error_rate"] = float(m["error_rate"]) * 100.0
                    if m.get("db_pool_utilization", 0) > 80.0:
                        anoms["db_pool_utilization"] = float(m["db_pool_utilization"])

                    fp = FingerprintBuilder.build(
                        incident_id=f"agent-eval-{state['service_name']}",
                        primary_service=state["service_name"],
                        affected_services=[state["service_name"]],
                        telemetry_anomalies=anoms,
                        error_logs=[],
                        hypotheses=[f"Agent evaluation on {state['service_name']}"],
                    )
                    memories = await ReliabilityMemoryEngine.find_similar_incidents(
                        target_fingerprint=fp,
                        db=db,
                        min_similarity=0.20,
                        limit=3,
                    )
                except Exception as e:
                    logger.warning(f"Memory retrieval in agent failed: {e}")

            trace = f"Indexed memory search retrieved {len(memories)} historical candidates."
            return {
                "similar_memories": memories,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 4: Regression Check
        async def regression_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            # Check for active regression records or elevated post-remediation regression
            from backend.app.models.reliability import RegressionRecord
            reg_records: List[Dict[str, Any]] = []
            if db:
                from sqlalchemy import select
                stmt = select(RegressionRecord).where(
                    RegressionRecord.service_name == state["service_name"],
                    RegressionRecord.status.in_(["ACTIVE", "CONFIRMED"]),
                )
                res = await db.execute(stmt)
                reg_records = [
                    {
                        "id": r.id,
                        "metric_name": r.metric_name,
                        "classification": r.classification,
                        "regression_score": r.regression_score,
                    }
                    for r in res.scalars().all()
                ]

            trace = f"Regression check: {len(reg_records)} active regressions identified on {state['service_name']}."
            return {
                "regressions": reg_records,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 5: Predictive Evaluation
        async def predictive_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            preds = await PredictiveReliabilityEngine.analyze_service(
                service_name=state["service_name"],
                window_seconds=120,
                db=db,
            )
            pred_dicts = [p.to_dict() for p in preds]
            critical_preds = [p for p in pred_dicts if p["warning_level"] in ["CRITICAL", "WARNING"]]
            trace = f"Predictive evaluation: {len(critical_preds)} impending threshold breaches (shortest TTE: {min([p['time_to_exhaustion_minutes'] for p in critical_preds if p['time_to_exhaustion_minutes']], default='N/A')}m)."
            return {
                "predictions": pred_dicts,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 6: SLO Assessment
        async def slo_assessment_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            burn_reports = await SLOIntelligenceEngine.get_burn_rates(
                service_name=state["service_name"],
                db=db,
            )
            fast_burns = [b for b in burn_reports if b["fast_burn_alert"]]
            trace = f"SLO assessment: {len(burn_reports)} SLOs monitored, {len(fast_burns)} fast-burn alerts active."
            return {
                "slo_reports": burn_reports,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 7: Decision Policy Engine (Deterministic SRE Guardrails)
        async def decision_policy_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            reasons: List[str] = []
            recommended_action = "act-investigate-topology"
            execution_mode = "RECOMMENDATION_ONLY"
            risk_level = "LOW"
            escalate = False
            confidence = 0.85

            # Guardrail 1: Active Post-Remediation Regression -> Immediate Human Escalation
            if state["regressions"]:
                reasons.append("Active post-remediation regression detected: metric degradation recurred after previous intervention.")
                recommended_action = "act-escalate-human-review"
                execution_mode = "HUMAN_APPROVAL"
                risk_level = "HIGH"
                escalate = True
                confidence = 0.95

            # Guardrail 2: Critical Fast Burn Alert (> 14.4x)
            elif any(b["fast_burn_alert"] for b in state["slo_reports"]):
                reasons.append("Emergency SLO Fast Burn alert (>14.4x): 30-day error budget will be fully consumed in under 48 hours.")
                recommended_action = "act-apply-rate-limit"
                execution_mode = "HUMAN_APPROVAL"
                risk_level = "CRITICAL"
                escalate = True
                confidence = 0.92

            # Guardrail 3: Predictive Resource Exhaustion Horizon
            elif any(p["warning_level"] == "CRITICAL" for p in state["predictions"]):
                crit = next(p for p in state["predictions"] if p["warning_level"] == "CRITICAL")
                reasons.append(f"Critical exhaustion horizon detected on {crit['metric_name']}: TTE is {crit['time_to_exhaustion_minutes']:.1f} minutes.")
                if crit["metric_name"] == "db_pool_utilization":
                    recommended_action = "act-reset-db-pool"
                elif crit["metric_name"] == "memory_utilization":
                    recommended_action = "act-clear-cache"
                else:
                    recommended_action = "act-restart-service"
                execution_mode = "HUMAN_APPROVAL"
                risk_level = "MEDIUM"
                confidence = 0.90

            # Guardrail 4: Proven Historical Memory Reuse
            elif state["similar_memories"]:
                top = state["similar_memories"][0]
                hist = top["incident"]
                if top["similarity"]["overall_similarity_score"] >= 0.50 and hist["remediation_outcome"] == "SUSTAINED_SUCCESS":
                    if hist["remediation_actions"]:
                        act_id = hist["remediation_actions"][0]["action_id"]
                        recommended_action = act_id
                        reasons.append(f"Matching historical pattern from incident {hist['incident_id']} where '{act_id}' achieved sustained recovery.")
                        execution_mode = "CONTROLLED_AUTONOMOUS"
                        risk_level = "LOW"
                        confidence = 0.88
                else:
                    reasons.append(f"Historical incident matched ({top['similarity']['overall_similarity_score']:.2f} similarity) but requires human verification.")
                    execution_mode = "HUMAN_APPROVAL"
                    confidence = 0.80

            else:
                reasons.append("Telemetry indicators nominal; continuous background observability active.")
                recommended_action = "act-maintain-monitoring"
                execution_mode = "RECOMMENDATION_ONLY"
                risk_level = "LOW"
                confidence = 0.90

            decision = {
                "action_id": recommended_action,
                "execution_mode": execution_mode,
                "risk_level": risk_level,
                "rationale": "; ".join(reasons),
                "confidence_score": confidence,
                "escalate_to_human": escalate,
            }

            trace = f"Decision Policy synthesized: action='{recommended_action}', mode='{execution_mode}', risk='{risk_level}', confidence={confidence:.2f}."
            return {
                "decision": decision,
                "escalation_flag": escalate,
                "reasoning_trace": state["reasoning_trace"] + [trace],
            }

        # Node 8: Audit Logging
        async def audit_node(state: ReliabilityAgentState) -> Dict[str, Any]:
            if db:
                try:
                    audit = AuditLog(
                        actor_type="AGENT",
                        actor_id="LangGraphReliabilityAgent",
                        action="RELIABILITY_ASSESSMENT",
                        resource_type="Service",
                        resource_id=state["service_name"],
                        incident_id=state.get("incident_id"),
                        details=json.dumps({
                            "decision": state["decision"],
                            "reasoning_trace": state["reasoning_trace"],
                            "timestamp": state["timestamp"],
                        }),
                    )
                    db.add(audit)
                    await db.commit()
                except Exception as e:
                    logger.warning(f"Failed to record audit log: {e}")
                    await db.rollback()

            return state

        # Assemble graph edges
        workflow.add_node("telemetry", telemetry_node)
        workflow.add_node("anomaly_context", anomaly_context_node)
        workflow.add_node("memory_retrieval", memory_retrieval_node)
        workflow.add_node("regression", regression_node)
        workflow.add_node("predictive", predictive_node)
        workflow.add_node("slo_assessment", slo_assessment_node)
        workflow.add_node("decision_policy", decision_policy_node)
        workflow.add_node("audit", audit_node)

        workflow.set_entry_point("telemetry")
        workflow.add_edge("telemetry", "anomaly_context")
        workflow.add_edge("anomaly_context", "memory_retrieval")
        workflow.add_edge("memory_retrieval", "regression")
        workflow.add_edge("regression", "predictive")
        workflow.add_edge("predictive", "slo_assessment")
        workflow.add_edge("slo_assessment", "decision_policy")
        workflow.add_edge("decision_policy", "audit")
        workflow.add_edge("audit", END)

        compiled_app = workflow.compile()
        final_state = await compiled_app.ainvoke(initial_state)

        # Cache last run result
        cls._last_run_cache = final_state
        return final_state
