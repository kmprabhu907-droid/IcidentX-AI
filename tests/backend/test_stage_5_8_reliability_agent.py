"""
INCIDENTX AI - Stage 5.8 LangGraph Autonomous Reliability Intelligence Agent Tests
Validates the full 8-node reasoning loop (telemetry, anomaly context, memory retrieval,
regression check, predictive evaluation, SLO assessment, decision policy, and audit logging),
deterministic safety guardrails, and FastAPI agent endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.reliability import RegressionRecord
from backend.app.services.agents import LangGraphReliabilityAgent


# 1. LangGraph 8-node loop execution completes
@pytest.mark.asyncio
async def test_01_langgraph_agent_full_loop_execution(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert result is not None
    assert result["service_name"] == "order-service"
    assert "telemetry_data" in result
    assert "decision" in result
    assert len(result["reasoning_trace"]) >= 6


# 2. Telemetry node gathers live metrics
@pytest.mark.asyncio
async def test_02_telemetry_node_populates_data(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    telemetry = result["telemetry_data"]
    assert "cpu_utilization" in telemetry
    assert "memory_utilization" in telemetry
    assert any("Gathered streaming telemetry" in t for t in result["reasoning_trace"])


# 3. Anomaly context node executes
@pytest.mark.asyncio
async def test_03_anomaly_context_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert "active_anomalies" in result
    assert any("active anomalies" in t for t in result["reasoning_trace"])


# 4. Memory retrieval node executes
@pytest.mark.asyncio
async def test_04_memory_retrieval_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert "similar_memories" in result
    assert any("Indexed memory search" in t for t in result["reasoning_trace"])


# 5. Regression check node executes
@pytest.mark.asyncio
async def test_05_regression_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert "regressions" in result
    assert any("Regression check" in t for t in result["reasoning_trace"])


# 6. Predictive evaluation node executes
@pytest.mark.asyncio
async def test_06_predictive_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert "predictions" in result
    assert len(result["predictions"]) >= 1
    assert any("Predictive evaluation" in t for t in result["reasoning_trace"])


# 7. SLO assessment node executes
@pytest.mark.asyncio
async def test_07_slo_assessment_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    assert "slo_reports" in result
    assert any("SLO assessment" in t for t in result["reasoning_trace"])


# 8. Decision policy node produces structured decision
@pytest.mark.asyncio
async def test_08_decision_policy_structure(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    decision = result["decision"]
    assert "action_id" in decision
    assert "execution_mode" in decision
    assert "risk_level" in decision
    assert "rationale" in decision
    assert "confidence_score" in decision


# 9. Guardrail 1: Active regression escalates to human review
@pytest.mark.asyncio
async def test_09_guardrail_regression_escalation(db_session: AsyncSession):
    # Insert an active regression record
    reg = RegressionRecord(
        service_name="payment-service",
        metric_name="latency_p95_ms",
        baseline_value=45.0,
        post_remediation_value=50.0,
        current_value=850.0,
        regression_score=0.92,
        classification="CONFIRMED_REGRESSION",
        status="ACTIVE",
    )
    db_session.add(reg)
    await db_session.commit()

    result = await LangGraphReliabilityAgent.assess(
        service_name="payment-service",
        db=db_session,
    )
    decision = result["decision"]
    assert decision["action_id"] == "act-escalate-human-review"
    assert decision["execution_mode"] == "HUMAN_APPROVAL"
    assert decision["escalate_to_human"] is True
    assert "regression" in decision["rationale"].lower()


# 10. Audit logging node writes to audit_logs table
@pytest.mark.asyncio
async def test_10_audit_logging_node(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="auth-service",
        db=db_session,
    )
    stmt = select(AuditLog).where(
        AuditLog.actor_id == "LangGraphReliabilityAgent",
        AuditLog.resource_id == "auth-service",
    )
    res = await db_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) >= 1
    assert "RELIABILITY_ASSESSMENT" in logs[-1].action


# 11. Reasoning trace contains comprehensive SRE diagnostic narrative
@pytest.mark.asyncio
async def test_11_reasoning_trace_comprehensiveness(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        db=db_session,
    )
    trace = result["reasoning_trace"]
    # Should trace through all nodes
    assert any("streaming telemetry" in t for t in trace)
    assert any("anomalies" in t for t in trace)
    assert any("memory search" in t for t in trace)
    assert any("Regression check" in t for t in trace)
    assert any("Predictive evaluation" in t for t in trace)
    assert any("SLO assessment" in t for t in trace)
    assert any("Decision Policy" in t for t in trace)


# 12. Last-run caching retains most recent assessment
@pytest.mark.asyncio
async def test_12_last_run_caching(db_session: AsyncSession):
    result = await LangGraphReliabilityAgent.assess(
        service_name="api-gateway",
        db=db_session,
    )
    last_run = LangGraphReliabilityAgent.get_last_run()
    assert last_run is not None
    assert last_run["service_name"] == "api-gateway"


# 13. Assessment with incident_id context
@pytest.mark.asyncio
async def test_13_assessment_with_incident_context(db_session: AsyncSession):
    inc = Incident(
        title="Live Evaluation Incident",
        summary="Evaluation in progress",
        severity="SEV-2",
        status="INVESTIGATING",
        impact_scope="order-service",
    )
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    result = await LangGraphReliabilityAgent.assess(
        service_name="order-service",
        incident_id=inc.id,
        db=db_session,
    )
    assert result["incident_id"] == inc.id


# 14. API: POST /api/v1/reliability/agent/assess with defaults
@pytest.mark.asyncio
async def test_14_api_agent_assess_default(client: AsyncClient):
    resp = await client.post("/api/v1/reliability/agent/assess")
    assert resp.status_code == 200
    data = resp.json()
    assert "decision" in data
    assert "reasoning_trace" in data


# 15. API: POST /api/v1/reliability/agent/assess with service_name
@pytest.mark.asyncio
async def test_15_api_agent_assess_service_filter(client: AsyncClient):
    resp = await client.post(
        "/api/v1/reliability/agent/assess",
        json={"service_name": "order-service"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "order-service"
    assert "action_id" in data["decision"]


# 16. API: GET /api/v1/reliability/agent/last-run
@pytest.mark.asyncio
async def test_16_api_agent_last_run(client: AsyncClient):
    # Trigger assessment first
    await client.post(
        "/api/v1/reliability/agent/assess",
        json={"service_name": "inventory-service"},
    )

    resp = await client.get("/api/v1/reliability/agent/last-run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "inventory-service"
    assert "decision" in data
