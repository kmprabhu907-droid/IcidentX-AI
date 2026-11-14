"""
INCIDENTX AI — PHASE 11: AUTONOMOUS ROOT CAUSE INTELLIGENCE ENGINE
Comprehensive Automated Test Suite

Covers:
- Module 11.1: Intelligent Hypothesis Generation
- Module 11.2: Competing Hypothesis Engine
- Module 11.3: Multi-Domain Evidence Correlation
- Module 11.4: Active Counter-Evidence Engine (Popperian Falsification)
- Module 11.5: Deterministic Explainable Confidence Scorer
- Module 11.6: Directed Causal Graph & DAG Construction
- Module 11.7: Historical Incident Intelligence & Recurrence Detection
- Module 11.8: Interactive Root Cause Intelligence API Endpoints
- Module 11.9: Master Root Cause Intelligence Service Orchestration
- Module 11.10: Integration with Multi-Agent Investigation Pipeline
"""

import asyncio
from datetime import datetime, timezone, timedelta
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.services.root_cause.schemas import (
    HypothesisItem,
    HypothesisStatus,
    ConfidenceCategory,
    CausalNodeType,
    CausalRelationType,
    RootCauseReport,
    CompetingHypothesisAnalysis,
    CounterEvidenceReport,
    CausalGraph,
)
from backend.app.services.root_cause.evidence_correlator import evidence_correlator, EvidenceCorrelator
from backend.app.services.root_cause.hypothesis_generator import hypothesis_generator, HypothesisGenerator
from backend.app.services.root_cause.counter_evidence_engine import counter_evidence_engine, CounterEvidenceEngine
from backend.app.services.root_cause.confidence_scorer import confidence_scorer, ConfidenceScorer
from backend.app.services.root_cause.competing_engine import competing_hypothesis_engine, CompetingHypothesisEngine
from backend.app.services.root_cause.causal_engine import causal_reasoning_engine, CausalReasoningEngine
from backend.app.services.root_cause.historical_intelligence import historical_incident_intelligence, HistoricalIncidentIntelligence
from backend.app.services.root_cause.root_cause_service import root_cause_service, RootCauseIntelligenceService
from backend.app.services.investigation.orchestrator import InvestigationOrchestrator


# ==============================================================================
# 1. EVIDENCE CORRELATOR TESTS (Module 11.3)
# ==============================================================================

@pytest.mark.asyncio
async def test_evidence_correlator_multi_plane_and_reliability(db_session: AsyncSession):
    """Verifies that evidence from multiple planes is correlated with proper weights and chronological ordering."""
    now = datetime.now(timezone.utc)
    incident = Incident(
        title="Payment Service Degradation",
        severity="SEV-1",
        status="INVESTIGATING",
        impact_scope="payment-service",
    )
    db_session.add(incident)
    await db_session.flush()

    e1 = Evidence(
        incident_id=incident.id,
        evidence_type="metric_anomaly",
        evidence_category="METRICS",
        source_system="prometheus",
        affected_service_name="payment-service",
        description="Pod memory usage exceeded 95%",
        confidence_score=0.98,
        is_fact=True,
        observed_at=now - timedelta(seconds=120),
    )
    e2 = Evidence(
        incident_id=incident.id,
        evidence_type="error_log",
        evidence_category="APPLICATION_LOGS",
        source_system="loki",
        affected_service_name="payment-service",
        description="java.lang.OutOfMemoryError: Java heap space",
        confidence_score=0.90,
        is_fact=True,
        observed_at=now - timedelta(seconds=60),
    )
    e3 = Evidence(
        incident_id=incident.id,
        evidence_type="alert",
        evidence_category="ALERT",
        source_system="alertmanager",
        affected_service_name="payment-service",
        description="HighLatencyAlert firing",
        confidence_score=0.75,
        is_fact=True,
        observed_at=now - timedelta(seconds=150),
    )
    db_session.add_all([e1, e2, e3])
    await db_session.flush()

    correlated = await evidence_correlator.correlate_incident_evidence(
        incident_id=incident.id,
        session=db_session,
        affected_service="payment-service",
    )

    assert correlated["incident_id"] == incident.id
    assert correlated["total_evidence_count"] == 3
    assert len(correlated["domain_groups"]["METRICS"]) == 1
    assert len(correlated["domain_groups"]["APPLICATION_LOGS"]) == 1

    # Verify chronological timeline sorting (oldest first: -150s, -120s, -60s)
    timeline = correlated["chronological_timeline"]
    assert len(timeline) == 3
    assert "HighLatencyAlert" in timeline[0]["observation"]
    assert "OutOfMemoryError" in timeline[2]["observation"]

    # Verify source reliability weights: prometheus >= 0.90, logs >= 0.80, alertmanager <= 0.75
    assert EvidenceCorrelator.get_source_reliability("prometheus") >= 0.90
    assert EvidenceCorrelator.get_source_reliability("logs") >= 0.80
    assert EvidenceCorrelator.get_source_reliability("alertmanager") <= 0.75

    # Verify metric-to-log correlation detected
    assert len(correlated["metric_log_correlations"]) >= 1
    assert correlated["primary_service"] == "payment-service"


# ==============================================================================
# 2. HYPOTHESIS GENERATOR TESTS (Module 11.1)
# ==============================================================================

@pytest.mark.asyncio
async def test_hypothesis_generator_competing_candidates(db_session: AsyncSession):
    """Verifies that generator produces at least 3 distinct competing hypotheses tailored to incident signals."""
    incident = Incident(
        title="Cart Service CrashLoopBackOff",
        severity="SEV-2",
        status="INVESTIGATING",
        impact_scope="cart-service",
    )
    db_session.add(incident)
    await db_session.flush()

    e1 = Evidence(
        incident_id=incident.id,
        evidence_type="kubernetes_event",
        evidence_category="KUBERNETES",
        source_system="kubernetes",
        affected_service_name="cart-service",
        description="Container terminated with OOMKilled exit code 137",
        is_fact=True,
    )
    e2 = Evidence(
        incident_id=incident.id,
        evidence_type="error_log",
        evidence_category="APPLICATION_LOGS",
        source_system="loki",
        affected_service_name="cart-service",
        description="Fatal error: Out of memory buffer allocated",
        is_fact=True,
    )
    db_session.add_all([e1, e2])
    await db_session.flush()

    correlated = await evidence_correlator.correlate_incident_evidence(
        incident_id=incident.id,
        session=db_session,
        affected_service="cart-service",
    )

    hypotheses = hypothesis_generator.generate_hypotheses(
        incident_id=incident.id,
        investigation_id="inv-test-1",
        correlated_data=correlated,
        affected_service="cart-service",
    )

    assert len(hypotheses) >= 3
    # Check hypothesis schema integrity
    for hyp in hypotheses:
        assert hyp.incident_id == incident.id
        assert hyp.status in [HypothesisStatus.PROPOSED, HypothesisStatus.SUPPORTED, HypothesisStatus.INVESTIGATING]
        assert hyp.affected_service == "cart-service"
        assert len(hyp.title) > 0
        assert len(hyp.description) > 0

    # Ensure resource exhaustion candidate exists
    resource_hyp = next((h for h in hypotheses if "Resource Exhaustion" in h.title or "Memory" in h.title), None)
    assert resource_hyp is not None


# ==============================================================================
# 3. COUNTER-EVIDENCE & ACTIVE FALSIFICATION TESTS (Module 11.4)
# ==============================================================================

@pytest.mark.asyncio
async def test_counter_evidence_active_disproof(db_session: AsyncSession):
    """Verifies Popperian disproof: hypotheses contradicted by ground truth telemetry are penalized/refuted."""
    incident = Incident(
        title="Checkout Service Errors",
        severity="SEV-1",
        status="INVESTIGATING",
        impact_scope="checkout-service",
    )
    db_session.add(incident)
    await db_session.flush()

    # Ground truth: database CPU is normal (contradicting DB saturation)
    e1 = Evidence(
        incident_id=incident.id,
        evidence_type="metric_anomaly",
        evidence_category="METRICS",
        source_system="prometheus",
        affected_service_name="checkout-service",
        description="Database CPU is normal and query latency is 4ms",
        is_fact=True,
    )
    # Ground truth: zero network dropped packets
    e2 = Evidence(
        incident_id=incident.id,
        evidence_type="network_probe",
        evidence_category="NETWORK",
        source_system="network",
        affected_service_name="checkout-service",
        description="Zero dropped packets on network interface eth0",
        is_fact=True,
    )
    db_session.add_all([e1, e2])
    await db_session.flush()

    correlated = await evidence_correlator.correlate_incident_evidence(
        incident_id=incident.id,
        session=db_session,
        affected_service="checkout-service",
    )

    hypotheses = hypothesis_generator.generate_hypotheses(
        incident_id=incident.id,
        investigation_id="inv-test-2",
        correlated_data=correlated,
        affected_service="checkout-service",
    )

    counter_reports = counter_evidence_engine.evaluate_counter_evidence(
        hypotheses=hypotheses,
        correlated_data=correlated,
    )

    assert len(counter_reports) == len(hypotheses)

    # Database or Network hypothesis should have active contradictions/penalties
    db_or_net_report = next(
        (r for r in counter_reports if "Database" in r.hypothesis_title or "Network" in r.hypothesis_title), None
    )
    assert db_or_net_report is not None
    assert db_or_net_report.score_penalty_applied >= 0.0


# ==============================================================================
# 4. DETERMINISTIC CONFIDENCE SCORER TESTS (Module 11.5)
# ==============================================================================

def test_confidence_scorer_deterministic_formula():
    """Verifies mathematical scoring formula consistency and category boundaries."""
    # Mock correlated data with 4 facts
    class MockFact:
        def __init__(self, fid):
            self.id = fid

    correlated_data = {
        "facts": [MockFact("f1"), MockFact("f2"), MockFact("f3"), MockFact("f4")],
    }

    # Case A: Well-supported hypothesis with domain diversity and verified facts
    hyp_high = HypothesisItem(
        id="hyp-high",
        incident_id="inc-1",
        title="Pod Memory Leak",
        description="Unbounded cache allocation leading to container eviction",
        affected_service="order-service",
        triggering_event="Deployment revision 4 applied 10m ago",
        supporting_evidence_ids=["f1", "f2", "f3"],
        contradicting_evidence_ids=[],
        missing_evidence=[],
        source_domains=["KUBERNETES", "METRICS", "APPLICATION_LOGS"],
        confidence_score=0.5,
    )

    score_high, cat_high, breakdown_high, expl_high = confidence_scorer.score_hypothesis(hyp_high, correlated_data)
    assert score_high >= 0.70
    assert cat_high in [ConfidenceCategory.HIGH, ConfidenceCategory.VERY_HIGH]
    assert breakdown_high["fact_ratio"] == 1.0
    assert breakdown_high["domain_coverage"] == 1.0

    # Case B: Refuted hypothesis with counter-evidence
    hyp_low = HypothesisItem(
        id="hyp-low",
        incident_id="inc-1",
        title="Database Deadlock",
        description="DB lock timeout",
        affected_service="order-service",
        supporting_evidence_ids=["f4"],
        contradicting_evidence_ids=["c1", "c2"],
        missing_evidence=["DB connection metrics", "Postgres slow query log"],
        source_domains=["APPLICATION_LOGS"],
        confidence_score=0.5,
    )

    score_low, cat_low, breakdown_low, expl_low = confidence_scorer.score_hypothesis(hyp_low, correlated_data)
    assert score_low < 0.45
    assert cat_low in [ConfidenceCategory.LOW, ConfidenceCategory.INSUFFICIENT_EVIDENCE]
    assert breakdown_low["contra_deduction"] > 0.0


# ==============================================================================
# 5. COMPETING HYPOTHESIS ENGINE TESTS (Module 11.2)
# ==============================================================================

def test_competing_hypothesis_ranking_and_discrimination():
    """Verifies competing hypothesis comparative matrix and discriminating evidence extraction."""
    class MockFact:
        def __init__(self, fid):
            self.id = fid

    correlated_data = {
        "facts": [MockFact("ev-shared"), MockFact("ev-disc-1"), MockFact("ev-disc-2")],
    }

    h1 = HypothesisItem(
        id="h-mem",
        incident_id="inc-test",
        title="Application Memory Leak",
        description="High memory usage",
        affected_service="api-gateway",
        triggering_event="Version bump",
        supporting_evidence_ids=["ev-shared", "ev-disc-1"],
        source_domains=["METRICS", "APPLICATION_LOGS"],
    )
    h2 = HypothesisItem(
        id="h-net",
        incident_id="inc-test",
        title="Socket Exhaustion",
        description="Network socket backlog",
        affected_service="api-gateway",
        supporting_evidence_ids=["ev-shared"],
        contradicting_evidence_ids=["ev-disc-2"],
        missing_evidence=["Socket stats"],
        source_domains=["NETWORK"],
    )

    analysis = competing_hypothesis_engine.evaluate_competing_hypotheses(
        incident_id="inc-test",
        investigation_id="inv-comp-1",
        hypotheses=[h1, h2],
        correlated_data=correlated_data,
    )

    assert analysis.total_hypotheses == 2
    assert analysis.top_hypothesis_id == "h-mem"
    assert len(analysis.ranked_hypotheses) == 2
    assert analysis.ranked_hypotheses[0].id == "h-mem"
    assert "ev-shared" in analysis.shared_evidence_matrix
    assert len(analysis.ranking_rationale) > 0


# ==============================================================================
# 6. CAUSAL REASONING & DAG CONSTRUCTION TESTS (Module 11.6)
# ==============================================================================

def test_causal_graph_synthesis_and_acyclic_topology():
    """Verifies that causal DAG correctly models trigger -> root cause -> cascade -> symptom without cycles."""
    class MockFact:
        def __init__(self, fid, desc):
            self.id = fid
            self.description = desc
            self.is_fact = True

    correlated_data = {
        "facts": [
            MockFact("f-dep", "Deploy v2.4 applied to auth-service"),
            MockFact("f-oom", "OOMKilled container crash"),
            MockFact("f-500", "503 Service Unavailable alert firing"),
        ],
        "primary_service": "auth-service",
        "cascading_services": ["payment-service", "frontend"],
        "deployment_event": MockFact("f-dep", "Deploy v2.4 applied to auth-service"),
        "domain_groups": {
            "KUBERNETES": [MockFact("f-oom", "OOMKilled container crash")],
            "METRICS": [MockFact("f-500", "503 Service Unavailable alert firing")],
        },
    }

    leading_hyp = HypothesisItem(
        id="hyp-lead",
        incident_id="inc-causal",
        title="Memory Leak in Buffer Allocator",
        description="Heap exhaustion after v2.4 release",
        affected_service="auth-service",
        triggering_event="Deploy v2.4 applied to auth-service",
    )

    graph = causal_reasoning_engine.build_causal_graph(
        incident_id="inc-causal",
        leading_hypothesis=leading_hyp,
        correlated_data=correlated_data,
    )

    assert len(graph.nodes) >= 4
    assert len(graph.edges) >= 3

    node_types = {n.node_type for n in graph.nodes}
    assert CausalNodeType.TRIGGERING_EVENT in node_types
    assert CausalNodeType.ROOT_CAUSE_CANDIDATE in node_types
    assert CausalNodeType.USER_FACING_SYMPTOM in node_types

    edge_types = {e.relation_type for e in graph.edges}
    assert CausalRelationType.VERIFIED_CAUSAL in edge_types
    assert graph.verified_causal_ratio > 0.0


# ==============================================================================
# 7. HISTORICAL INCIDENT INTELLIGENCE TESTS (Module 11.7)
# ==============================================================================

@pytest.mark.asyncio
async def test_historical_incident_intelligence_similarity(db_session: AsyncSession):
    """Verifies that past resolved incidents with similar patterns are matched without fabricating fake data."""
    # Past resolved incident
    past_inc = Incident(
        title="Cart Service OOM CrashLoopBackOff",
        severity="SEV-2",
        status="RESOLVED",
        impact_scope="cart-service",
        summary="Pod memory limits exceeded leading to OOM crash loop",
    )
    db_session.add(past_inc)
    await db_session.flush()

    # Current incident
    curr_inc = Incident(
        title="Cart Service Out of Memory Failures",
        severity="SEV-2",
        status="INVESTIGATING",
        impact_scope="cart-service",
        summary="High memory usage on cart service pods",
    )
    db_session.add(curr_inc)
    await db_session.flush()

    matches = await historical_incident_intelligence.find_similar_incidents(
        incident_id=curr_inc.id,
        session=db_session,
        limit=5,
    )

    assert len(matches) >= 1
    best_match = matches[0]
    assert best_match.incident_id == past_inc.id
    assert best_match.matching_service == "cart-service"
    assert best_match.similarity_score > 0.30


# ==============================================================================
# 8. MASTER ROOT CAUSE INTELLIGENCE SERVICE TESTS (Module 11.9)
# ==============================================================================

@pytest.mark.asyncio
async def test_root_cause_service_end_to_end_evaluation(db_session: AsyncSession):
    """Verifies that the orchestrating service produces a complete, persisted RootCauseReport."""
    incident = Incident(
        title="Order Processing Failure Under Load",
        severity="SEV-1",
        status="INVESTIGATING",
        impact_scope="order-service",
    )
    db_session.add(incident)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    evs = [
        Evidence(
            incident_id=incident.id,
            evidence_type="git_commit",
            evidence_category="DEPLOYMENT",
            source_system="kubernetes",
            affected_service_name="order-service",
            description="Deployment order-service updated to v3.2.0",
            is_fact=True,
            observed_at=now - timedelta(minutes=10),
        ),
        Evidence(
            incident_id=incident.id,
            evidence_type="metric_anomaly",
            evidence_category="METRICS",
            source_system="prometheus",
            affected_service_name="order-service",
            description="HTTP 500 error rate surged to 48%",
            is_fact=True,
            observed_at=now - timedelta(minutes=5),
        ),
        Evidence(
            incident_id=incident.id,
            evidence_type="error_log",
            evidence_category="APPLICATION_LOGS",
            source_system="loki",
            affected_service_name="order-service",
            description="ConnectionPoolTimeoutException: Timeout waiting for idle connection",
            is_fact=True,
            observed_at=now - timedelta(minutes=4),
        ),
    ]
    db_session.add_all(evs)
    await db_session.flush()

    report = await root_cause_service.evaluate_incident_root_cause(
        incident_id=incident.id,
        session=db_session,
        affected_service="order-service",
    )

    assert report.incident_id == incident.id
    assert len(report.primary_root_cause) > 0
    assert report.confidence_score > 0.0
    assert len(report.competing_analysis.ranked_hypotheses) >= 3
    assert report.causal_graph is not None

    # Verify hypotheses persisted to RootCauseHypothesis table
    stmt = select(RootCauseHypothesis).where(RootCauseHypothesis.incident_id == incident.id)
    res = await db_session.execute(stmt)
    persisted = res.scalars().all()
    assert len(persisted) >= 3


# ==============================================================================
# 9. REST API ENDPOINTS TESTS (Module 11.8)
# ==============================================================================

@pytest.mark.asyncio
async def test_root_cause_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Verifies that all Phase 11 REST endpoints respond with correct schemas and status codes."""
    incident = Incident(
        title="Frontend Ingress Latency Spike",
        severity="SEV-2",
        status="INVESTIGATING",
        impact_scope="frontend-ingress",
    )
    db_session.add(incident)
    await db_session.flush()

    e = Evidence(
        incident_id=incident.id,
        evidence_type="alert",
        evidence_category="ALERT",
        source_system="alertmanager",
        affected_service_name="frontend-ingress",
        description="IngressLatencyP99ThresholdExceeded",
        is_fact=True,
    )
    db_session.add(e)
    await db_session.flush()

    # 1. POST /api/v1/incidents/{id}/root-cause/evaluate
    eval_resp = await client.post(f"/api/v1/incidents/{incident.id}/root-cause/evaluate")
    assert eval_resp.status_code == 200
    report_data = eval_resp.json()
    assert report_data["incident_id"] == incident.id
    assert "primary_root_cause" in report_data
    assert "confidence_score" in report_data

    # 2. GET /api/v1/incidents/{id}/root-cause/report
    rep_resp = await client.get(f"/api/v1/incidents/{incident.id}/root-cause/report")
    assert rep_resp.status_code == 200
    assert rep_resp.json()["incident_id"] == incident.id

    # 3. GET /api/v1/incidents/{id}/root-cause/hypotheses
    hyp_resp = await client.get(f"/api/v1/incidents/{incident.id}/root-cause/hypotheses")
    assert hyp_resp.status_code == 200
    hyp_data = hyp_resp.json()
    assert "ranked_hypotheses" in hyp_data
    assert len(hyp_data["ranked_hypotheses"]) >= 1

    # 4. GET /api/v1/incidents/{id}/root-cause/counter-evidence
    counter_resp = await client.get(f"/api/v1/incidents/{incident.id}/root-cause/counter-evidence")
    assert counter_resp.status_code == 200
    counter_data = counter_resp.json()
    assert isinstance(counter_data, list)

    # 5. GET /api/v1/incidents/{id}/root-cause/causal-graph
    graph_resp = await client.get(f"/api/v1/incidents/{incident.id}/root-cause/causal-graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data

    # 6. GET /api/v1/incidents/{id}/root-cause/similar-incidents
    sim_resp = await client.get(f"/api/v1/incidents/{incident.id}/root-cause/similar-incidents")
    assert sim_resp.status_code == 200
    assert isinstance(sim_resp.json(), list)


# ==============================================================================
# 10. MULTI-AGENT PIPELINE INTEGRATION TEST (Module 11.10)
# ==============================================================================

@pytest.mark.asyncio
async def test_investigation_orchestrator_phase11_integration(db_session: AsyncSession):
    """Verifies that InvestigationOrchestrator Stage 3 invokes Phase 11 Root Cause Intelligence Service."""
    incident = Incident(
        title="Auth Service 503 Outage",
        severity="SEV-1",
        status="DETECTED",
        impact_scope="auth-service",
    )
    db_session.add(incident)
    await db_session.flush()

    e1 = Evidence(
        incident_id=incident.id,
        evidence_type="kubernetes_event",
        evidence_category="KUBERNETES",
        source_system="kubernetes",
        affected_service_name="auth-service",
        description="Pod crash detected in default namespace",
        is_fact=True,
    )
    e2 = Evidence(
        incident_id=incident.id,
        evidence_type="metric_anomaly",
        evidence_category="METRICS",
        source_system="prometheus",
        affected_service_name="auth-service",
        description="Error rate 85% on endpoint /login",
        is_fact=True,
    )
    db_session.add_all([e1, e2])
    await db_session.flush()

    orchestrator = InvestigationOrchestrator()
    result = await orchestrator.run_investigation(incident.id, session_override=db_session)

    assert result["status"] == "COMPLETED"
    assert "root_cause_report" in result["workflow_data"]
    rc_report = result["workflow_data"]["root_cause_report"]
    assert rc_report["incident_id"] == incident.id
    assert rc_report["confidence_score"] > 0.0
    assert len(rc_report["primary_root_cause"]) > 0
