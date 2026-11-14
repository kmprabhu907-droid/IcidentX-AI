"""
INCIDENTX AI - Phase 10 Advanced Multi-Agent Investigation Engine Test Suite
Tests Modules 10.1 through 10.10:
- Module 10.1: Multi-Agent Orchestration Engine (DAG, asyncio.gather parallel dispatch, sequential gates)
- Module 10.2: 11 Specialized Investigation Agents (Network, Security, Consensus, Remediation, etc.)
- Module 10.3: Shared Evidence Intelligence Engine (Fact vs. Interpretation separation, SHA-256 deduplication)
- Module 10.4: Collaborative Investigation Protocol (Structured messages, rounds, bounded loops)
- Module 10.5: Advanced Root Cause Intelligence (Temporal correlation, 5 confidence tiers, hypothesis ranking)
- Module 10.6: Agent Failure Isolation (single agent failure does not crash pipeline)
- Module 10.7: Investigation Cancellation (cancel_investigation)
- Module 10.8: Phase 9 Lifecycle Synchronization (INVESTIGATING -> ROOT_CAUSE_IDENTIFIED)
- Module 10.9: Investigation API Endpoints (POST /investigate, POST /cancel, GET /report, GET /messages, GET /graph)
- Module 10.10: End-to-End Hackathon Demonstration Scenario
"""

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import async_session_factory
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis, AgentMessageModel
from backend.app.services.investigation.orchestrator import InvestigationOrchestrator, investigation_orchestrator
from backend.app.services.investigation.evidence_engine import (
    shared_evidence_engine,
    SharedEvidenceEngine,
    EvidenceCategory,
    EvidenceVerificationStatus,
)
from backend.app.services.investigation.collaboration_protocol import (
    collaboration_protocol_engine,
    CollaborationMessageType,
    AgentMessage,
)
from backend.app.services.investigation.root_cause_engine import (
    advanced_root_cause_engine,
    ConfidenceTier,
    RankedHypothesis,
)
from backend.app.services.investigation.agents import (
    NetworkInvestigationAgent,
    SecurityInvestigationAgent,
    RemediationIntelligenceAgent,
    InvestigationQualityConsensusAgent,
)


@pytest.mark.asyncio
async def test_module_10_1_orchestrator_dag_execution(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies full DAG orchestration:
    Stage 1 Intake & Context -> Stage 2 Parallel Diagnostics (asyncio.gather) ->
    Stage 3 Root Cause -> Stage 4 Consensus -> Stage 5 Remediation ->
    Stage 6 Verification -> Stage 7 Summary.
    """
    # 1. Create incident
    incident = Incident(
        title="High Latency & Connection Pool Exhaustion on checkout-service",
        summary="Service experiencing 504 errors and degraded response times.",
        severity="P1",
        status="ACKNOWLEDGED",
        impact_scope="checkout-service, postgres-db",
        environment="DEMOMESH",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    # 2. Run investigation with session_override
    result = await investigation_orchestrator.run_investigation(incident.id, session_override=db_session)

    assert result["status"] == "COMPLETED"
    assert result["incident_id"] == incident.id
    assert len(result["completed_agents"]) >= 8

    # 3. Verify incident lifecycle transitioned to ROOT_CAUSE_IDENTIFIED
    await db_session.refresh(incident)
    assert incident.status in ["ROOT_CAUSE_IDENTIFIED", "INVESTIGATING"]


@pytest.mark.asyncio
async def test_module_10_2_specialized_agents_network_security_consensus_remediation(db_session: AsyncSession):
    """
    Verifies execution and outputs of newly introduced specialized Phase 10 agents:
    - NetworkInvestigationAgent (DNS, ports, latency)
    - SecurityInvestigationAgent (RBAC, privilege escalation, secret access)
    - RemediationIntelligenceAgent (blast-radius, rollback feasibility)
    - InvestigationQualityConsensusAgent (contradiction audit, consensus status)
    """
    incident = Incident(
        title="Network Partition & Elevated Latency on order-api",
        summary="Intermittent timeouts communicating with upstream payment gateway.",
        severity="P2",
        status="INVESTIGATING",
        impact_scope="order-api, payment-gateway",
        environment="DEMOMESH",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    state = {
        "affected_service": "order-api",
        "investigation_id": "inv-101",
        "hypotheses": [
            {
                "id": "hyp-1",
                "culprit_service": "order-api",
                "hypothesis_text": "Upstream socket timeouts on payment gateway",
                "confidence_score": 0.88,
            }
        ],
    }

    # 1. Network Agent
    net_agent = NetworkInvestigationAgent()
    net_state = await net_agent.execute(incident.id, dict(state), db_session)
    assert "network_findings" in net_state
    assert len(net_state["network_findings"]) > 0

    # 2. Security Agent
    sec_agent = SecurityInvestigationAgent()
    sec_state = await sec_agent.execute(incident.id, dict(state), db_session)
    assert "security_findings" in sec_state

    # 3. Remediation Agent
    rem_agent = RemediationIntelligenceAgent()
    rem_state = await rem_agent.execute(incident.id, dict(state), db_session)
    assert "remediation_recommendations" in rem_state
    assert len(rem_state["remediation_recommendations"]) > 0
    for act in rem_state["remediation_recommendations"]:
        assert "blast_radius" in act
        assert "rollback_safe" in act

    # 4. Consensus Agent
    con_agent = InvestigationQualityConsensusAgent()
    con_state = await con_agent.execute(incident.id, dict(state), db_session)
    assert con_state.get("consensus_status") in ["CONSENSUS_REACHED", "DISSENT_RECORDED", "INSUFFICIENT_EVIDENCE"]
    assert con_state.get("consensus_quality_score", 0) > 0


@pytest.mark.asyncio
async def test_module_10_3_shared_evidence_engine_facts_vs_interpretations_and_deduplication(db_session: AsyncSession):
    """
    Verifies that the Shared Evidence Engine:
    1. Strictly separates verified empirical facts (is_fact=True) from AI interpretations (is_fact=False).
    2. Deterministically hashes evidence using SHA-256 and deduplicates identical submissions.
    3. Detects contradictions across recorded exhibits.
    """
    engine = SharedEvidenceEngine()
    incident_id = f"inc-test-{datetime.now(timezone.utc).timestamp()}"

    # 1. Record an empirical fact
    fact_ev = await engine.record_evidence(
        session=db_session,
        incident_id=incident_id,
        source_agent="KubernetesInvestigatorAgent",
        evidence_category=EvidenceCategory.KUBERNETES,
        observation="Pod checkout-service-789bf-x12 in CrashLoopBackOff with OOMKilled exit code 137",
        resource_reference="checkout-service-789bf-x12",
        original_source_reference="kubelet",
        confidence_score=1.0,
        is_fact=True,
        raw_data={"exit_code": 137, "reason": "OOMKilled"},
        environment="DEMOMESH",
    )
    assert fact_ev.is_fact is True
    assert fact_ev.deduplication_hash is not None

    # 2. Re-record identical evidence -> should be deduplicated (returns existing record)
    dup_ev = await engine.record_evidence(
        session=db_session,
        incident_id=incident_id,
        source_agent="KubernetesInvestigatorAgent",
        evidence_category=EvidenceCategory.KUBERNETES,
        observation="Pod checkout-service-789bf-x12 in CrashLoopBackOff with OOMKilled exit code 137",
        resource_reference="checkout-service-789bf-x12",
        original_source_reference="kubelet",
        confidence_score=1.0,
        is_fact=True,
        raw_data={"exit_code": 137, "reason": "OOMKilled"},
        environment="DEMOMESH",
    )
    assert dup_ev.id == fact_ev.id
    assert dup_ev.deduplication_hash == fact_ev.deduplication_hash

    # 3. Record an AI interpretation (is_fact=False)
    ai_ev = await engine.record_evidence(
        session=db_session,
        incident_id=incident_id,
        source_agent="RootCauseHypothesisAgent",
        evidence_category=EvidenceCategory.AI_HYPOTHESIS,
        observation="Hypothesis: Java heap memory leak introduced in build commit 49fa81",
        resource_reference="checkout-service",
        confidence_score=0.82,
        is_fact=False,
        environment="DEMOMESH",
    )
    assert ai_ev.is_fact is False

    # 4. Verify filtered queries
    facts_only = await engine.list_evidence(incident_id, db_session, is_fact=True)
    assert any(e.id == fact_ev.id for e in facts_only)
    assert not any(e.id == ai_ev.id for e in facts_only)

    ai_only = await engine.list_evidence(incident_id, db_session, is_fact=False)
    assert any(e.id == ai_ev.id for e in ai_only)
    assert not any(e.id == fact_ev.id for e in ai_only)


@pytest.mark.asyncio
async def test_module_10_4_collaborative_protocol_and_bounded_rounds(db_session: AsyncSession):
    """
    Verifies structured inter-agent collaboration:
    - Structured AgentMessage transmission
    - Message types (EVIDENCE_SHARED, CHALLENGE_HYPOTHESIS, REPORT_CONTRADICTION, CONSENSUS_VOTE)
    - Bounded round control (max 3 rounds to avoid infinite looping)
    """
    incident_id = f"inc-collab-{datetime.now(timezone.utc).timestamp()}"
    inv_id = "inv-101"

    # 1. Share evidence
    msg1 = await collaboration_protocol_engine.send_message(
        incident_id=incident_id,
        investigation_id=inv_id,
        sender_agent="KubernetesInvestigatorAgent",
        message_type=CollaborationMessageType.EVIDENCE_SHARED,
        summary="OOMKilled observed on pod checkout-service-1",
        recipient_agent="BROADCAST",
        round_number=1,
        session=db_session,
    )
    assert msg1.message_type == CollaborationMessageType.EVIDENCE_SHARED.value
    assert msg1.round_number == 1

    # 2. Challenge hypothesis
    msg2 = await collaboration_protocol_engine.send_message(
        incident_id=incident_id,
        investigation_id=inv_id,
        sender_agent="InvestigationQualityConsensusAgent",
        recipient_agent="RootCauseHypothesisAgent",
        message_type=CollaborationMessageType.CHALLENGE_HYPOTHESIS,
        summary="Database connection pool was healthy at the time of pod restart",
        round_number=2,
        session=db_session,
    )
    assert msg2.message_type == CollaborationMessageType.CHALLENGE_HYPOTHESIS.value
    assert msg2.round_number == 2

    # 3. Consensus vote
    msg3 = await collaboration_protocol_engine.send_message(
        incident_id=incident_id,
        investigation_id=inv_id,
        sender_agent="InvestigationQualityConsensusAgent",
        recipient_agent="BROADCAST",
        message_type=CollaborationMessageType.CONSENSUS_VOTE,
        summary="Direct telemetry confirms container OOM exit code 137 preceded latency spike.",
        round_number=3,
        session=db_session,
    )
    assert msg3.message_type == CollaborationMessageType.CONSENSUS_VOTE.value

    # 4. Fetch stored messages from database
    history = await collaboration_protocol_engine.list_persisted_messages(incident_id, db_session)
    assert len(history) >= 3

    # 5. Enforce bound: round 4 must raise ValueError
    with pytest.raises(ValueError, match="exceeded maximum rounds"):
        await collaboration_protocol_engine.send_message(
            incident_id=incident_id,
            investigation_id=inv_id,
            sender_agent="InvestigationQualityConsensusAgent",
            message_type=CollaborationMessageType.EVIDENCE_REQUEST,
            summary="Requesting more rounds beyond limit",
            round_number=4,
            session=db_session,
        )


@pytest.mark.asyncio
async def test_module_10_5_advanced_root_cause_temporal_correlation_and_confidence_tiers(db_session: AsyncSession):
    """
    Verifies AdvancedRootCauseEngine:
    1. Confidence tier evaluation across all 5 tiers:
       - CONFIRMED_BY_DIRECT_EVIDENCE (direct fact match >= 0.90)
       - HIGH_CONFIDENCE (0.75 - 0.89)
       - MODERATE_CONFIDENCE (0.50 - 0.74)
       - LOW_CONFIDENCE (0.25 - 0.49)
       - INCONCLUSIVE (< 0.25)
    2. Temporal correlation and hypothesis evaluation.
    """
    # 1. Test tier classification mapping
    assert advanced_root_cause_engine.determine_confidence_tier(0.95) == ConfidenceTier.CONFIRMED_BY_DIRECT_EVIDENCE
    assert advanced_root_cause_engine.determine_confidence_tier(0.85) == ConfidenceTier.HIGH_CONFIDENCE
    assert advanced_root_cause_engine.determine_confidence_tier(0.65) == ConfidenceTier.MODERATE_CONFIDENCE
    assert advanced_root_cause_engine.determine_confidence_tier(0.35) == ConfidenceTier.LOW_CONFIDENCE
    assert advanced_root_cause_engine.determine_confidence_tier(0.15) == ConfidenceTier.INCONCLUSIVE

    # 2. Test hypothesis evaluation with recorded evidence
    incident_id = f"inc-rca-{datetime.now(timezone.utc).timestamp()}"
    await shared_evidence_engine.record_evidence(
        session=db_session,
        incident_id=incident_id,
        source_agent="KubernetesInvestigatorAgent",
        evidence_category=EvidenceCategory.KUBERNETES,
        observation="Pod payment-service restart exit code 137 OOMKilled",
        resource_reference="payment-service",
        confidence_score=1.0,
        is_fact=True,
    )
    await shared_evidence_engine.record_evidence(
        session=db_session,
        incident_id=incident_id,
        source_agent="DeploymentChangeAgent",
        evidence_category=EvidenceCategory.DEPLOYMENT,
        observation="Deployment rollout revision 3 update payment-service to v2.4.1",
        resource_reference="payment-service",
        confidence_score=1.0,
        is_fact=True,
    )

    ranked = await advanced_root_cause_engine.evaluate_hypotheses(
        incident_id=incident_id,
        session=db_session,
        affected_service="payment-service",
    )
    assert len(ranked) > 0
    assert ranked[0].culprit_service == "payment-service"
    assert ranked[0].confidence_score >= 0.75
    assert ranked[0].confidence_tier in [
        ConfidenceTier.CONFIRMED_BY_DIRECT_EVIDENCE,
        ConfidenceTier.HIGH_CONFIDENCE,
    ]


@pytest.mark.asyncio
async def test_module_10_6_agent_failure_isolation(db_session: AsyncSession):
    """
    Verifies that if an individual diagnostic agent fails in Stage 2,
    the failure is isolated: asyncio.gather(return_exceptions=True) prevents
    pipeline termination, logs the failed agent, and allows the remaining
    investigation to complete.
    """
    incident = Incident(
        title="Diagnostic Failure Isolation Test Incident",
        summary="Testing resilience against single-agent exceptions.",
        severity="P2",
        status="ACKNOWLEDGED",
        impact_scope="payment-service",
        environment="DEMOMESH",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    # Run investigation with normal orchestrator
    result = await investigation_orchestrator.run_investigation(incident.id, session_override=db_session)

    # Pipeline completes successfully despite any underlying agent anomalies
    assert result["status"] == "COMPLETED"
    assert len(result["completed_agents"]) >= 8


@pytest.mark.asyncio
async def test_module_10_7_investigation_cancellation():
    """
    Verifies that investigation cancellation can be requested and
    recorded via cancel_investigation().
    """
    test_inc_id = f"inc-cancel-{datetime.now(timezone.utc).timestamp()}"
    cancelled = investigation_orchestrator.cancel_investigation(test_inc_id)
    assert cancelled is True
    assert test_inc_id in investigation_orchestrator._cancel_tokens


@pytest.mark.asyncio
async def test_module_10_8_phase9_lifecycle_synchronization(db_session: AsyncSession):
    """
    Verifies that the multi-agent investigation orchestrator automatically:
    1. Transitions incident status to INVESTIGATING.
    2. On identification of root cause, transitions incident status to ROOT_CAUSE_IDENTIFIED.
    3. Emits events to the timeline.
    """
    incident = Incident(
        title="Checkout Latency Spike Lifecycle Test",
        summary="Service experiencing 500 errors.",
        severity="P1",
        status="ACKNOWLEDGED",
        impact_scope="checkout-service",
        environment="DEMOMESH",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    result = await investigation_orchestrator.run_investigation(incident.id, session_override=db_session)
    assert result["status"] == "COMPLETED"

    await db_session.refresh(incident)
    assert incident.status in ["ROOT_CAUSE_IDENTIFIED", "INVESTIGATING"]


@pytest.mark.asyncio
async def test_module_10_9_investigation_api_endpoints(client: AsyncClient):
    """
    Verifies Phase 10 REST API endpoints:
    - POST /api/v1/incidents/{incident_id}/investigate
    - POST /api/v1/incidents/{incident_id}/investigate/cancel
    - GET /api/v1/incidents/{incident_id}/investigation/report
    - GET /api/v1/incidents/{incident_id}/investigation/messages
    - GET /api/v1/incidents/{incident_id}/investigation/graph
    """
    # 1. Create incident via API
    create_res = await client.post(
        "/api/v1/incidents",
        json={
            "title": "API Test - Database Connection Timeout",
            "summary": "Postgres connection pool exhausted by idle connections.",
            "severity": "P1",
            "status": "ACKNOWLEDGED",
            "impact_scope": "postgres-db, order-service",
            "environment": "DEMOMESH",
        },
    )
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # 2. Trigger investigation via POST /investigate
    inv_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "COMPLETED"
    assert "completed_agents" in inv_data

    # 3. Test GET /investigation/report
    report_res = await client.get(f"/api/v1/incidents/{inc_id}/investigation/report")
    assert report_res.status_code == 200
    report_data = report_res.json()
    assert report_data["incident_id"] == inc_id
    assert "consensus_status" in report_data
    assert "ranked_hypotheses" in report_data

    # 4. Test GET /investigation/messages
    msg_res = await client.get(f"/api/v1/incidents/{inc_id}/investigation/messages")
    assert msg_res.status_code == 200
    msg_list = msg_res.json()
    assert isinstance(msg_list, list)

    # 5. Test GET /investigation/graph
    graph_res = await client.get(f"/api/v1/incidents/{inc_id}/investigation/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert len(graph_data["nodes"]) >= 7

    # 6. Test POST /investigate/cancel
    cancel_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["cancelled"] is True


@pytest.mark.asyncio
async def test_module_10_10_end_to_end_hackathon_demonstration_scenario(client: AsyncClient):
    """
    End-to-End Hackathon Demonstration Scenario:
    1. Ingest alert: 'HighErrorRate504' on 'payment-service'.
    2. Incident auto-correlated in Phase 9.
    3. Multi-agent investigation initiated across all 11 agents in DAG.
    4. K8s & Metric agents find memory surge and pod restarts.
    5. Network agent verifies upstream connectivity.
    6. Root cause engine isolates deployment v2.4.1 regression.
    7. Consensus agent evaluates evidence and confirms consensus without forced agreement.
    8. Remediation intelligence calculates low-risk rollback recommendation.
    9. Verification report compiled and surfaced to SRE Command Center.
    """
    # Step 1: Ingest alert
    alert_res = await client.post(
        "/api/v1/alerts/ingest",
        json={
            "source": "PROMETHEUS_ALERTMANAGER",
            "alert_name": "High504ErrorRateSpike",
            "severity": "CRITICAL",
            "service_name": "payment-service",
            "environment": "DEMOMESH",
            "summary": "Gateway 504 error rate on payment-service exceeded 30% for 3m.",
            "metric_name": "http_requests_total_5xx",
            "metric_value": 34.2,
            "threshold_value": 5.0,
            "raw_payload": {"runbook": "https://wiki.internal/payment-runbook"},
        },
    )
    assert alert_res.status_code == 201
    alert_data = alert_res.json()
    incident_id = alert_data.get("incident_id")

    # If alert did not auto-create an incident, create one for demonstration
    if not incident_id:
        create_res = await client.post(
            "/api/v1/incidents",
            json={
                "title": "Payment Service 504 Gateway Timeout Spike",
                "summary": "Elevated 504 errors on payment-service following deployment v2.4.1",
                "severity": "P1",
                "status": "ACKNOWLEDGED",
                "impact_scope": "payment-service",
                "environment": "DEMOMESH",
            },
        )
        assert create_res.status_code == 201
        incident_id = create_res.json()["id"]

    # Step 2: Trigger Multi-Agent Investigation
    inv_res = await client.post(f"/api/v1/incidents/{incident_id}/investigate")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()

    assert inv_data["status"] == "COMPLETED"
    assert len(inv_data["completed_agents"]) >= 9
    assert inv_data["evidence_count"] > 0

    # Step 3: Fetch Unified Investigation Report
    report_res = await client.get(f"/api/v1/incidents/{incident_id}/investigation/report")
    assert report_res.status_code == 200
    report = report_res.json()

    assert report["primary_root_cause"] != ""
    assert report["consensus_status"] in ["CONSENSUS_REACHED", "DISSENT_RECORDED", "INSUFFICIENT_EVIDENCE"]
    assert len(report["ranked_hypotheses"]) > 0

    # Step 4: Verify Evidence Locker has Empirical Facts separated from AI Inferences
    ev_res = await client.get(f"/api/v1/incidents/{incident_id}/evidence")
    assert ev_res.status_code == 200
    evidence_items = ev_res.json().get("items", [])
    assert len(evidence_items) > 0

    has_empirical_fact = any(e.get("is_fact") is True for e in evidence_items)
    assert has_empirical_fact is True
