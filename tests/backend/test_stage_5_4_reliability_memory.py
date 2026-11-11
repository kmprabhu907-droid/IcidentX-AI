"""
INCIDENTX AI - Stage 5.4 Reliability Memory Engine Tests
Covers all 20 validation scenarios for 20-dimension memory entry assembly,
pre-indexing, multi-criteria search, fingerprint-ranked similarity retrieval,
missing data handling, remediation learning & side effects, 6 explainable answers,
and FastAPI reliability endpoints.
"""

import json
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.app.core.database import get_db
from backend.app.models.incident import Incident
from backend.app.models.investigation import Evidence, RootCauseHypothesis
from backend.app.models.reliability import IncidentMemory, RegressionRecord
from backend.app.models.remediation import RemediationAction
from backend.app.services.observability.regression.fingerprint import FingerprintBuilder
from backend.app.services.reliability_memory import (
    HistoricalMemoryEntry,
    MemorySearchExplanation,
    ReliabilityMemoryEngine,
    RemediationLearner,
    SIDE_EFFECT_REGISTRY,
)


@pytest.fixture
def sample_incident_data():
    return {
        "title": "PostgreSQL Connection Pool Exhaustion on order-service",
        "summary": "Connection pool reached 100% capacity causing cascading timeouts",
        "severity": "SEV-1",
        "status": "RESOLVED",
        "impact_scope": "order-service, postgres-db",
        "mttr_seconds": 420.0,
    }


# 1. Full 20-dimension memory entry assembly
@pytest.mark.asyncio
async def test_01_build_memory_entry_full_dimensions(db_session: AsyncSession, sample_incident_data):
    # Create incident
    inc = Incident(**sample_incident_data)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    # Add supporting and contradicting evidence
    ev1 = Evidence(
        incident_id=inc.id,
        evidence_type="error_log",
        source_system="order-service",
        description="FATAL: remaining connection slots are reserved for non-replication superuser connections",
        confidence_score=0.95,
        verification_status="VERIFIED",
        is_contradictory=False,
    )
    ev2 = Evidence(
        incident_id=inc.id,
        evidence_type="metric_anomaly",
        source_system="postgres-db",
        description="Database connection pool utilization at 100%",
        confidence_score=0.99,
        verification_status="VERIFIED",
        is_contradictory=False,
    )
    ev3 = Evidence(
        incident_id=inc.id,
        evidence_type="cpu_spike",
        source_system="order-service",
        description="CPU utilization remained nominal at 25%",
        confidence_score=0.40,
        verification_status="DISPROVEN",
        is_contradictory=True,
    )
    db_session.add_all([ev1, ev2, ev3])

    # Add hypotheses
    h1 = RootCauseHypothesis(
        incident_id=inc.id,
        hypothesis_text="Database connection leak caused pool exhaustion in order-service",
        probability_score=0.92,
        status="ACCEPTED",
        is_confirmed_root_cause=True,
    )
    db_session.add(h1)

    # Add remediation action
    rem = RemediationAction(
        incident_id=inc.id,
        action_id="act-reset-db-pool",
        name="Reset Database Connection Pool",
        description="Drain and cycle stale connections in pool",
        action_type="db_pool",
        expected_outcome="Recover pool connections",
        idempotency_key=f"idem-act-reset-{inc.id}",
        target_service_name="postgres-db",
        risk_level="MEDIUM",
        status="EXECUTED",
        verification_status="VERIFIED",
        rollback_status="NONE",
    )
    db_session.add(rem)
    await db_session.commit()

    entry = await ReliabilityMemoryEngine.build_memory_entry(inc.id, db_session)
    assert entry is not None
    assert entry.incident_id == inc.id
    assert entry.title == sample_incident_data["title"]
    assert entry.primary_service == "order-service"
    assert "postgres-db" in entry.affected_services
    assert entry.severity == "SEV-1"
    assert entry.confirmed_root_cause == "Database connection leak caused pool exhaustion in order-service"
    assert len(entry.supporting_evidence) == 2
    assert len(entry.contradicting_evidence) == 1
    assert len(entry.error_signatures) >= 1
    assert entry.remediation_outcome == "SUSTAINED_SUCCESS"
    assert "Active long-running transaction rollback" in entry.side_effects
    assert len(entry.learned_lessons) >= 1


# 2. Verification of non-existent incident
@pytest.mark.asyncio
async def test_02_build_memory_entry_nonexistent(db_session: AsyncSession):
    entry = await ReliabilityMemoryEngine.build_memory_entry("non-existent-id", db_session)
    assert entry is None


# 3. Pre-computation and database indexing
@pytest.mark.asyncio
async def test_03_index_incident_memory(db_session: AsyncSession, sample_incident_data):
    inc = Incident(**sample_incident_data)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    indexed = await ReliabilityMemoryEngine.index_incident_memory(inc.id, db_session)
    assert indexed is not None
    assert indexed.incident_id == inc.id
    assert indexed.primary_service == "order-service"
    assert indexed.remediation_outcome is not None
    assert "order-service" in indexed.search_vector


# 4. Re-indexing updates existing record
@pytest.mark.asyncio
async def test_04_reindex_incident_memory_updates(db_session: AsyncSession, sample_incident_data):
    inc = Incident(**sample_incident_data)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    idx1 = await ReliabilityMemoryEngine.index_incident_memory(inc.id, db_session)
    assert idx1 is not None

    # Update incident
    inc.severity = "SEV-2"
    await db_session.commit()

    idx2 = await ReliabilityMemoryEngine.index_incident_memory(inc.id, db_session)
    assert idx2.id == idx1.id
    assert idx2.severity == "SEV-2"


# 5. Multi-criteria search by service and severity
@pytest.mark.asyncio
async def test_05_search_memory_filters(db_session: AsyncSession):
    inc1 = Incident(
        title="Auth Service Redis Timeout",
        summary="Redis latency spike",
        severity="SEV-3",
        status="RESOLVED",
        impact_scope="auth-service",
    )
    inc2 = Incident(
        title="Payment Service Gateway Timeout",
        summary="Upstream gateway unreachable",
        severity="SEV-1",
        status="RESOLVED",
        impact_scope="payment-service",
    )
    db_session.add_all([inc1, inc2])
    await db_session.commit()

    # Search by service
    results_auth = await ReliabilityMemoryEngine.search_memory(db_session, service_name="auth-service")
    assert any(r.incident_id == inc1.id for r in results_auth)
    assert not any(r.incident_id == inc2.id for r in results_auth)

    # Search by severity
    results_sev1 = await ReliabilityMemoryEngine.search_memory(db_session, severity="SEV-1")
    assert any(r.incident_id == inc2.id for r in results_sev1)
    assert not any(r.incident_id == inc1.id for r in results_sev1)


# 6. Keyword text search across memory corpus
@pytest.mark.asyncio
async def test_06_search_memory_text_query(db_session: AsyncSession):
    inc = Incident(
        title="Memory Leak in inventory-service worker",
        summary="Garbage collection pauses exceeded 5000ms",
        severity="SEV-2",
        status="RESOLVED",
        impact_scope="inventory-service",
    )
    db_session.add(inc)
    await db_session.commit()

    results = await ReliabilityMemoryEngine.search_memory(db_session, query_text="garbage collection")
    assert len(results) >= 1
    assert any(r.incident_id == inc.id for r in results)


# 7. Fingerprint-ranked similarity retrieval
@pytest.mark.asyncio
async def test_07_find_similar_incidents(db_session: AsyncSession):
    inc1 = Incident(
        title="DB connection pool leak in order-service",
        summary="Postgres connection starvation",
        severity="SEV-1",
        status="RESOLVED",
        impact_scope="order-service, postgres-db",
    )
    db_session.add(inc1)
    await db_session.commit()
    await db_session.refresh(inc1)

    # Target fingerprint with similar characteristics
    target_fp = FingerprintBuilder.build(
        incident_id="target-live-01",
        primary_service="order-service",
        affected_services=["order-service", "postgres-db"],
        telemetry_anomalies={"db_pool_utilization": 95.0, "latency_p95_ms": 500.0},
        error_logs=["Connection pool full"],
        hypotheses=["Database pool exhausted due to unclosed sessions"],
        severity="SEV-1",
    )

    matches = await ReliabilityMemoryEngine.find_similar_incidents(
        target_fingerprint=target_fp,
        db=db_session,
        min_similarity=0.30,
        limit=5,
    )
    assert len(matches) >= 1
    top_match = matches[0]
    assert top_match["incident"]["primary_service"] == "order-service"
    assert top_match["similarity"]["overall_similarity_score"] >= 0.30
    assert "explanation" in top_match


# 8. Missing data handling in similarity matching
@pytest.mark.asyncio
async def test_08_missing_data_similarity_handling():
    # Target with completely empty telemetry anomalies and error logs
    empty_fp = FingerprintBuilder.build(
        incident_id="empty-target",
        primary_service="unknown-service",
        affected_services=[],
        telemetry_anomalies={},
        error_logs=[],
        hypotheses=[],
        severity="SEV-4",
    )
    assert empty_fp.primary_service == "unknown-service"
    assert len(empty_fp.metric_anomaly_vector) == 0


# 9. Remediation learner: cold start / zero executions
@pytest.mark.asyncio
async def test_09_remediation_learner_cold_start(db_session: AsyncSession):
    summary = await RemediationLearner.get_action_learning("act-unknown-custom", db_session)
    assert summary.total_executions == 0
    assert summary.success_rate == 0.0
    assert "HUMAN_APPROVAL" in summary.reusable_advice


# 10. Remediation learner: empirical metrics calculation
@pytest.mark.asyncio
async def test_10_remediation_learner_empirical_metrics(db_session: AsyncSession):
    inc = Incident(title="Test Incident", severity="SEV-2", status="RESOLVED")
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    # Add 2 verified actions, 1 failed action
    a1 = RemediationAction(
        incident_id=inc.id,
        action_id="act-clear-cache",
        name="Clear Cache",
        description="Evict redis keys",
        action_type="cache",
        expected_outcome="Reduce cache memory and stale keys",
        idempotency_key=f"idem-clear-1-{inc.id}",
        target_service_name="redis-cache",
        status="EXECUTED",
        verification_status="VERIFIED",
        rollback_status="NONE",
    )
    a2 = RemediationAction(
        incident_id=inc.id,
        action_id="act-clear-cache",
        name="Clear Cache",
        description="Evict redis keys",
        action_type="cache",
        expected_outcome="Reduce cache memory and stale keys",
        idempotency_key=f"idem-clear-2-{inc.id}",
        target_service_name="redis-cache",
        status="EXECUTED",
        verification_status="VERIFIED",
        rollback_status="NONE",
    )
    a3 = RemediationAction(
        incident_id=inc.id,
        action_id="act-clear-cache",
        name="Clear Cache",
        description="Evict redis keys",
        action_type="cache",
        expected_outcome="Reduce cache memory and stale keys",
        idempotency_key=f"idem-clear-3-{inc.id}",
        target_service_name="redis-cache",
        status="FAILED",
        verification_status="FAILED",
        rollback_status="ROLLED_BACK",
    )
    db_session.add_all([a1, a2, a3])
    await db_session.commit()

    summary = await RemediationLearner.get_action_learning("act-clear-cache", db_session, target_service="redis-cache")
    assert summary.total_executions == 3
    assert summary.failed_count == 1
    assert summary.rollback_count == 1
    assert summary.success_rate == pytest.approx(0.667, 0.01)
    assert len(summary.known_side_effects) >= 1


# 11. Remediation learner: side effects documented
@pytest.mark.asyncio
async def test_11_remediation_learner_side_effects_registry():
    assert "act-clear-cache" in SIDE_EFFECT_REGISTRY
    assert any("stampede" in s.lower() for s in SIDE_EFFECT_REGISTRY["act-clear-cache"])
    assert "act-reset-db-pool" in SIDE_EFFECT_REGISTRY


# 12. Six standard memory explanation answers
@pytest.mark.asyncio
async def test_12_explain_memory_match():
    target_fp = FingerprintBuilder.build(
        incident_id="target-01",
        primary_service="order-service",
        affected_services=["order-service", "postgres-db"],
        telemetry_anomalies={"db_pool_utilization": 90.0},
        error_logs=["FATAL: remaining connection slots"],
        hypotheses=["DB connection starvation"],
        severity="SEV-1",
    )

    entry = HistoricalMemoryEntry(
        incident_id="hist-01",
        title="Historical DB Starvation",
        summary="Pool saturated",
        severity="SEV-1",
        status="RESOLVED",
        detected_at=None,
        resolved_at=None,
        mttr_seconds=300.0,
        primary_service="order-service",
        affected_services=["order-service", "postgres-db"],
        root_cause_category="RESOURCE_STARVATION",
        confirmed_root_cause="Connection leak in session handler",
        hypotheses=[],
        supporting_evidence=[],
        contradicting_evidence=[],
        telemetry_patterns={"db_pool_utilization": 92.0},
        error_signatures=["FATAL: remaining connection slots"],
        dependency_relationships={},
        remediation_actions=[],
        remediation_outcome="SUSTAINED_SUCCESS",
        learned_lessons=["Inspect session handler connection close logic."],
        side_effects=["Brief client reconnect latency"],
        regressions_count=0,
    )

    from backend.app.services.observability.regression.similarity import IncidentSimilarityEngine
    hist_fp = FingerprintBuilder.build(
        incident_id=entry.incident_id,
        primary_service=entry.primary_service,
        affected_services=entry.affected_services,
        telemetry_anomalies=entry.telemetry_patterns,
        error_logs=entry.error_signatures,
        hypotheses=[entry.summary],
        severity=entry.severity,
    )
    sim_res = IncidentSimilarityEngine.compare_fingerprints(target_fp, hist_fp)

    expl = ReliabilityMemoryEngine.explain_memory_match(target_fp, entry, sim_res)
    assert expl.why_selected != ""
    assert expl.similarity_score >= 0.5
    assert len(expl.evidence_matches) >= 1
    assert "Yes" in expl.previous_remediation_effective
    assert len(expl.reusable_lessons) >= 1


# 13. API: GET /api/v1/reliability/memory/incidents
@pytest.mark.asyncio
async def test_13_api_list_historical_incidents(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/incidents?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# 14. API: GET /api/v1/reliability/memory/incidents/{incident_id} 200
@pytest.mark.asyncio
async def test_14_api_get_incident_memory_success(client: AsyncClient, db_session: AsyncSession, sample_incident_data):
    inc = Incident(**sample_incident_data)
    db_session.add(inc)
    await db_session.commit()
    await db_session.refresh(inc)

    resp = await client.get(f"/api/v1/reliability/memory/incidents/{inc.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == inc.id
    assert data["primary_service"] == "order-service"


# 15. API: GET /api/v1/reliability/memory/incidents/{incident_id} 404
@pytest.mark.asyncio
async def test_15_api_get_incident_memory_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/incidents/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# 16. API: POST /api/v1/reliability/memory/search
@pytest.mark.asyncio
async def test_16_api_post_memory_search(client: AsyncClient, db_session: AsyncSession):
    inc = Incident(
        title="Search Test Cassandra Latency",
        summary="Cluster wide mutation lag",
        severity="SEV-2",
        status="RESOLVED",
        impact_scope="order-service",
    )
    db_session.add(inc)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/reliability/memory/search",
        json={"query_text": "Cassandra", "service_name": "order-service"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(m["title"] == "Search Test Cassandra Latency" for m in data["matches"])


# 17. API: GET /api/v1/reliability/memory/remediation-history all actions
@pytest.mark.asyncio
async def test_17_api_get_remediation_history_all(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/remediation-history")
    assert resp.status_code == 200
    data = resp.json()
    assert "actions" in data
    assert len(data["actions"]) >= 1


# 18. API: GET /api/v1/reliability/memory/remediation-history specific action
@pytest.mark.asyncio
async def test_18_api_get_remediation_history_specific(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/remediation-history?action_id=act-clear-cache")
    assert resp.status_code == 200
    data = resp.json()
    assert "action_learning" in data
    assert data["action_learning"]["action_id"] == "act-clear-cache"


# 19. API: GET /api/v1/reliability/memory/similar-incidents by service_name
@pytest.mark.asyncio
async def test_19_api_get_similar_incidents_by_service(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/similar-incidents?service_name=order-service")
    assert resp.status_code == 200
    data = resp.json()
    assert "target" in data
    assert data["target"]["primary_service"] == "order-service"
    assert "similar_incidents" in data


# 20. API: GET /api/v1/reliability/memory/similar-incidents missing params error
@pytest.mark.asyncio
async def test_20_api_get_similar_incidents_missing_params(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/memory/similar-incidents")
    assert resp.status_code == 400
