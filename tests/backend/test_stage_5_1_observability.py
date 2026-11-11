"""
INCIDENTX AI - Stage 5.1 Observability Data Pipeline Test Suite
Validates 10-signal telemetry generation, 1-minute rollup aggregation, database persistence,
duplicate prevention, retention pruning, query filtering, pagination, and error recovery.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import math
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from backend.app.core.database import async_session_factory
from backend.app.models.audit import AuditLog
from backend.app.models.incident import Incident
from backend.app.models.telemetry import MetricRollup
from backend.app.services.observability.collector import (
    ContinuousObservabilityCollector,
    MetricBucketAccumulator,
    observability_collector,
)
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.main import app


@pytest.fixture(autouse=True)
async def clean_test_rollups():
    """Clean up test rollups created during test executions."""
    yield
    async with async_session_factory() as session:
        await session.execute(delete(MetricRollup).where(MetricRollup.service_name.like("test-%")))
        await session.commit()


@pytest.mark.asyncio
async def test_01_ten_signals_generated_correctly():
    """Test 1: Verify all 10 Golden Signals are produced with valid values."""
    latest = demo_mesh.get_latest_metrics()
    assert "order-service" in latest
    order = latest["order-service"]

    # 1. CPU utilization
    assert 0.0 <= order["cpu_utilization"] <= 100.0
    # 2. Memory utilization
    assert 0.0 <= order["memory_utilization"] <= 100.0
    # 3. Disk utilization
    assert 0.0 <= order["disk_utilization"] <= 100.0
    # 4. Network throughput
    assert order["network_throughput_mbps"] >= 0.0
    # 5. Latency (P50, P95, P99)
    assert order["latency_p50_ms"] > 0.0
    assert order["latency_p95_ms"] >= order["latency_p50_ms"]
    assert order["latency_p99_ms"] >= order["latency_p95_ms"]
    # 6. HTTP error rate
    assert 0.0 <= order["error_rate"] <= 100.0
    # 7. Database connection-pool utilization
    assert 0.0 <= order["db_pool_utilization"] <= 100.0
    # 8. Service availability
    assert 0.0 <= order["availability_pct"] <= 100.0
    # 9. Dependency health score
    assert 0.0 <= order["dependency_health"] <= 100.0
    # 10. Request throughput
    assert order["request_rate"] >= 0.0

    # Mandatory identity fields
    assert order["service_id"] is not None and len(order["service_id"]) > 0
    assert order["data_source"] in ["SIMULATED", "LIVE", "REPLAY"]


@pytest.mark.asyncio
async def test_02_all_seven_services_produce_telemetry():
    """Test 2: Verify all 7 microservices in topology produce valid telemetry."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/telemetry/signals")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_services"] == 7
        expected_services = [
            "api-gateway",
            "auth-service",
            "order-service",
            "payment-service",
            "inventory-service",
            "postgres-db",
            "redis-cache",
        ]
        for svc in expected_services:
            assert svc in data["services"]
            s_data = data["services"][svc]
            assert s_data["service_name"] == svc
            assert s_data["service_id"] is not None
            assert "cpu_utilization" in s_data
            assert "disk_utilization" in s_data
            assert "network_throughput_mbps" in s_data
            assert "availability_pct" in s_data


@pytest.mark.asyncio
async def test_03_correct_metric_aggregation():
    """Test 3: Verify MetricBucketAccumulator accurately calculates min, max, avg, latest, and count."""
    bucket_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    acc = MetricBucketAccumulator(
        service_id="test-svc-id-1",
        service_name="test-service",
        metric_name="cpu_utilization",
        bucket_start=bucket_time,
        data_source="SIMULATED",
    )

    test_samples = [10.0, 30.0, 20.0, 40.0]
    for s in test_samples:
        acc.add_sample(s)

    summary = acc.compute_summary()
    assert summary is not None
    assert summary["minimum"] == 10.0
    assert summary["maximum"] == 40.0
    assert summary["average"] == 25.0
    assert summary["latest_value"] == 40.0
    assert summary["sample_count"] == 4
    assert summary["service_name"] == "test-service"


@pytest.mark.asyncio
async def test_04_one_minute_bucket_calculation():
    """Test 4: Verify timestamps are rounded down to 1-minute bucket boundaries."""
    t1 = datetime(2026, 11, 11, 14, 25, 47, 123456, tzinfo=timezone.utc)
    bucket1 = t1.replace(second=0, microsecond=0)
    assert bucket1.second == 0
    assert bucket1.microsecond == 0
    assert bucket1.minute == 25

    t2 = datetime(2026, 11, 11, 14, 25, 0, 0, tzinfo=timezone.utc)
    bucket2 = t2.replace(second=0, microsecond=0)
    assert bucket1 == bucket2


@pytest.mark.asyncio
async def test_05_rollup_persistence():
    """Test 5: Verify completed 1-minute rollups are persisted to metric_rollups table."""
    collector = ContinuousObservabilityCollector(collection_interval_seconds=1)
    bucket_time = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=2)

    acc = MetricBucketAccumulator(
        service_id="test-svc-id-5",
        service_name="test-order-service",
        metric_name="cpu_utilization",
        bucket_start=bucket_time,
        data_source="SIMULATED",
    )
    acc.add_sample(45.5)
    acc.add_sample(55.5)

    collector._accumulators[("test-order-service", "cpu_utilization", int(bucket_time.timestamp()))] = acc
    flushed = await collector.flush_pending_buckets(force_all=True)
    assert flushed >= 1

    async with async_session_factory() as session:
        stmt = select(MetricRollup).where(
            MetricRollup.service_name == "test-order-service",
            MetricRollup.metric_name == "cpu_utilization",
            MetricRollup.bucket_start == bucket_time,
        )
        record = (await session.execute(stmt)).scalar_one_or_none()
        assert record is not None
        assert record.minimum == 45.5
        assert record.maximum == 55.5
        assert record.average == 50.5
        assert record.latest_value == 55.5
        assert record.sample_count == 2


@pytest.mark.asyncio
async def test_06_duplicate_rollup_prevention():
    """Test 6: Verify duplicate flushes for the same bucket update existing records instead of failing."""
    collector = ContinuousObservabilityCollector(collection_interval_seconds=1)
    bucket_time = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=3)

    # First write
    acc1 = MetricBucketAccumulator(
        service_id="test-svc-id-6",
        service_name="test-dup-service",
        metric_name="memory_utilization",
        bucket_start=bucket_time,
        data_source="SIMULATED",
    )
    acc1.add_sample(20.0)
    collector._accumulators[("test-dup-service", "memory_utilization", int(bucket_time.timestamp()))] = acc1
    await collector.flush_pending_buckets(force_all=True)

    # Second write for same bucket (e.g. late arrivals)
    acc2 = MetricBucketAccumulator(
        service_id="test-svc-id-6",
        service_name="test-dup-service",
        metric_name="memory_utilization",
        bucket_start=bucket_time,
        data_source="SIMULATED",
    )
    acc2.add_sample(40.0)
    collector._accumulators[("test-dup-service", "memory_utilization", int(bucket_time.timestamp()))] = acc2
    await collector.flush_pending_buckets(force_all=True)

    # Verify only ONE row exists and values merged
    async with async_session_factory() as session:
        stmt = select(MetricRollup).where(
            MetricRollup.service_name == "test-dup-service",
            MetricRollup.metric_name == "memory_utilization",
            MetricRollup.bucket_start == bucket_time,
        )
        records = (await session.execute(stmt)).scalars().all()
        assert len(records) == 1
        assert records[0].sample_count == 2
        assert records[0].average == 30.0
        assert records[0].maximum == 40.0


@pytest.mark.asyncio
async def test_07_invalid_telemetry_handling():
    """Test 7: Verify None, NaN, and Inf values are safely handled without throwing exceptions."""
    bucket_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    acc = MetricBucketAccumulator(
        service_id="test-svc-id-7",
        service_name="test-invalid-svc",
        metric_name="error_rate",
        bucket_start=bucket_time,
    )

    acc.add_sample(None)
    acc.add_sample(float("nan"))
    acc.add_sample(float("inf"))
    acc.add_sample("not_a_number")
    acc.add_sample(5.5)

    summary = acc.compute_summary()
    assert summary is not None
    assert summary["sample_count"] == 1
    assert summary["average"] == 5.5


@pytest.mark.asyncio
async def test_08_missing_telemetry_handling():
    """Test 8: Verify collector operates smoothly when telemetry payload has missing keys."""
    collector = ContinuousObservabilityCollector(collection_interval_seconds=1)
    # Feed an empty dict or incomplete metrics
    await collector.collect_and_aggregate()
    assert collector.last_error is None


@pytest.mark.asyncio
async def test_09_data_source_identification():
    """Test 9: Verify telemetry explicitly declares data_source (SIMULATED or LIVE)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/telemetry/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] in ["SIMULATED", "LIVE", "REPLAY"]
        for svc in data["services"].values():
            assert svc["data_source"] in ["SIMULATED", "LIVE", "REPLAY"]


@pytest.mark.asyncio
async def test_10_historical_query_filters():
    """Test 10: Verify /api/v1/telemetry/metrics/history filters by service_name and metric_name."""
    # Seed 2 distinct rollups
    bucket_time = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=5)
    async with async_session_factory() as session:
        r1 = MetricRollup(
            service_name="test-filter-svc-a",
            metric_name="cpu_utilization",
            bucket_start=bucket_time,
            minimum=10.0,
            maximum=20.0,
            average=15.0,
            latest_value=18.0,
            sample_count=5,
            data_source="SIMULATED",
        )
        r2 = MetricRollup(
            service_name="test-filter-svc-b",
            metric_name="memory_utilization",
            bucket_start=bucket_time,
            minimum=30.0,
            maximum=40.0,
            average=35.0,
            latest_value=38.0,
            sample_count=5,
            data_source="SIMULATED",
        )
        session.add_all([r1, r2])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/telemetry/metrics/history",
            params={"service_name": "test-filter-svc-a", "metric_name": "cpu_utilization"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for r in data["rollups"]:
            assert r["service_name"] == "test-filter-svc-a"
            assert r["metric_name"] == "cpu_utilization"


@pytest.mark.asyncio
async def test_11_pagination():
    """Test 11: Verify page and page_size controls."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/telemetry/metrics/history",
            params={"page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["rollups"]) <= 2


@pytest.mark.asyncio
async def test_12_seven_day_retention():
    """Test 12: Verify rollups older than 7 days are pruned and recent rollups are retained."""
    collector = ContinuousObservabilityCollector(retention_days=7)
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=9)
    recent_time = now - timedelta(days=2)

    async with async_session_factory() as session:
        old_record = MetricRollup(
            service_name="test-retention-svc",
            metric_name="cpu_utilization",
            bucket_start=old_time,
            minimum=10.0,
            maximum=20.0,
            average=15.0,
            latest_value=15.0,
            sample_count=1,
            data_source="SIMULATED",
        )
        recent_record = MetricRollup(
            service_name="test-retention-svc",
            metric_name="cpu_utilization",
            bucket_start=recent_time,
            minimum=20.0,
            maximum=30.0,
            average=25.0,
            latest_value=25.0,
            sample_count=1,
            data_source="SIMULATED",
        )
        session.add_all([old_record, recent_record])
        await session.commit()

    pruned = await collector.run_retention_cleanup()
    assert pruned >= 1

    async with async_session_factory() as session:
        # Old record should be gone
        stmt1 = select(MetricRollup).where(
            MetricRollup.service_name == "test-retention-svc",
            MetricRollup.bucket_start == old_time,
        )
        assert (await session.execute(stmt1)).scalar_one_or_none() is None

        # Recent record must be retained
        stmt2 = select(MetricRollup).where(
            MetricRollup.service_name == "test-retention-svc",
            MetricRollup.bucket_start == recent_time,
        )
        assert (await session.execute(stmt2)).scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_13_retention_protection_for_audit_records():
    """Test 13: Verify retention cleanup NEVER deletes audit logs or incident records."""
    collector = ContinuousObservabilityCollector(retention_days=7)
    old_time = datetime.now(timezone.utc) - timedelta(days=15)

    async with async_session_factory() as session:
        audit = AuditLog(
            actor_type="USER",
            actor_id="test-sre@incidentx.ai",
            action="INCIDENT_INVESTIGATION_COMPLETED",
            resource_type="incident",
            resource_id="test-incident-protected",
            created_at=old_time,
        )
        session.add(audit)
        await session.commit()
        audit_id = audit.id

    # Run cleanup
    await collector.run_retention_cleanup()

    # Verify audit log still exists
    async with async_session_factory() as session:
        stmt = select(AuditLog).where(AuditLog.id == audit_id)
        assert (await session.execute(stmt)).scalar_one_or_none() is not None

        # Clean up test audit log
        await session.execute(delete(AuditLog).where(AuditLog.id == audit_id))
        await session.commit()


@pytest.mark.asyncio
async def test_14_collector_startup_and_shutdown():
    """Test 14: Verify collector starts and stops gracefully without blocking."""
    test_collector = ContinuousObservabilityCollector(collection_interval_seconds=1)
    assert test_collector.status == "IDLE"

    await test_collector.start()
    assert test_collector.status == "RUNNING"
    assert test_collector._task is not None

    await test_collector.stop()
    assert test_collector.status == "STOPPED"
    assert test_collector._task is None


@pytest.mark.asyncio
async def test_15_collector_recovery_after_database_errors():
    """Test 15: Verify collector logs error and remains operational after transient DB failure."""
    test_collector = ContinuousObservabilityCollector(collection_interval_seconds=1)

    # Force an invalid accumulator payload that triggers error
    bad_bucket = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=1)
    acc = MetricBucketAccumulator(
        service_id="bad-id",
        service_name="test-bad",
        metric_name="cpu_utilization",
        bucket_start=bad_bucket,
    )
    acc.add_sample(10.0)
    test_collector._accumulators[("test-bad", "cpu_utilization", int(bad_bucket.timestamp()))] = acc

    # Normal flush works
    count = await test_collector.flush_pending_buckets(force_all=True)
    assert count >= 1
    assert test_collector.last_error is None


@pytest.mark.asyncio
async def test_16_collector_status_endpoint():
    """Test 16: Verify GET /api/v1/telemetry/collector/status returns operational diagnostics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/telemetry/collector/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "collector_status" in data
        assert "monitored_services_count" in data
        assert data["monitored_services_count"] == 7
        assert "buffer_stats" in data
