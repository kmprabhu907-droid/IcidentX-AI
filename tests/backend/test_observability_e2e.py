"""
INCIDENTX AI - Observability & Incident Detection 5 End-to-End Scenarios Test Suite
Verifies the complete end-to-end detection, correlation, and automated incident triage pipeline:
1. Payment Gateway Latency (SEV-2)
2. Database Connection Pool Exhaustion (SEV-1)
3. Progressive Heap Memory Leak (Threshold & Baseline breach)
4. Redis Cache Outage & Refusal (Infrastructure failure)
5. Ingress Traffic Surge (Traffic Intelligence)
"""

import asyncio
import pytest
from sqlalchemy import select
from backend.app.core.database import async_session_factory
from backend.app.models.incident import Incident
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.observability.engine import observability_engine
from backend.app.services.simulation.chaos_controller import chaos_controller


@pytest.mark.asyncio
async def test_e2e_scenario_1_payment_gateway_latency():
    """Scenario 1: Payment Gateway Latency -> Downstream Timeouts -> SEV-2 Incident."""
    # Ensure mesh baseline is clean
    await chaos_controller.stop_all()

    # Inject payment latency fault
    await chaos_controller.inject("payment_latency", parameters={"latency_ms": 2500.0})

    # Execute simulation cycle and evaluate
    await demo_mesh.tick()
    alerts = await observability_engine.evaluate_cycle()

    # Assert alerts fired
    assert len(alerts) > 0
    services = {a.service_name for a in alerts}
    assert "payment-service" in services or "order-service" in services

    # Verify incident persisted in database
    async with async_session_factory() as session:
        stmt = select(Incident).where(Incident.summary.like("%payment-service%")).order_by(Incident.detected_at.desc())
        res = await session.execute(stmt)
        incident = res.scalars().first()
        assert incident is not None
        assert incident.severity in ["SEV-1", "SEV-2"]
        assert "payment" in incident.title.lower() or "payment" in incident.summary.lower()

    # Clean up
    await chaos_controller.stop_all()


@pytest.mark.asyncio
async def test_e2e_scenario_2_db_pool_exhaustion():
    """Scenario 2: DB Connection Pool Exhaustion -> Cascade 500s -> SEV-1 Incident."""
    await chaos_controller.stop_all()

    # Inject DB connection pool exhaustion
    await chaos_controller.inject("db_pool_exhaustion")

    # Tick simulation and evaluate
    await demo_mesh.tick()
    alerts = await observability_engine.evaluate_cycle()

    assert any(a.service_name == "postgres-db" for a in alerts)
    assert any(a.metric_name == "db_pool_utilization" for a in alerts)

    # Verify SEV-1 Incident created
    async with async_session_factory() as session:
        stmt = select(Incident).where(Incident.severity == "SEV-1").order_by(Incident.detected_at.desc())
        res = await session.execute(stmt)
        incident = res.scalars().first()
        assert incident is not None
        assert incident.status in ["DETECTED", "INVESTIGATING"]

    await chaos_controller.stop_all()


@pytest.mark.asyncio
async def test_e2e_scenario_3_memory_leak():
    """Scenario 3: Progressive Memory Leak -> Threshold and Baseline Breach."""
    await chaos_controller.stop_all()

    # Inject accelerated memory leak on order-service
    await chaos_controller.inject("memory_leak", target_service="order-service", parameters={"leak_rate": 8.0})

    # Advance several ticks to accumulate memory saturation past 85%
    for _ in range(6):
        await demo_mesh.tick()

    alerts = await observability_engine.evaluate_cycle()
    mem_alerts = [a for a in alerts if a.metric_name == "memory_utilization"]
    assert len(mem_alerts) > 0
    assert any(a.service_name == "order-service" for a in mem_alerts)

    await chaos_controller.stop_all()


@pytest.mark.asyncio
async def test_e2e_scenario_4_redis_outage():
    """Scenario 4: Redis Cache Outage -> Service-Specific Error Patterns."""
    await chaos_controller.stop_all()

    await chaos_controller.inject("redis_down")
    await demo_mesh.tick()
    alerts = await observability_engine.evaluate_cycle()

    # Redis or auth error alerts triggered
    assert any(a.service_name in ["redis-cache", "auth-service"] for a in alerts)

    await chaos_controller.stop_all()


@pytest.mark.asyncio
async def test_e2e_scenario_5_traffic_surge():
    """Scenario 5: Ingress Traffic Surge -> 5x Traffic Volume Alert."""
    await chaos_controller.stop_all()

    await chaos_controller.inject("traffic_surge", parameters={"multiplier": 5.0})
    await demo_mesh.tick()
    alerts = await observability_engine.evaluate_cycle()

    # Traffic intelligence detector must fire
    traffic_alerts = [a for a in alerts if a.metric_name == "traffic_surge"]
    assert len(traffic_alerts) > 0
    assert any(a.service_name == "api-gateway" for a in traffic_alerts)

    await chaos_controller.stop_all()
