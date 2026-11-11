"""
INCIDENTX AI - Stage 5.6 SLO & Error Budget Intelligence Tests
Validates SLI computations, remaining error budgets (1 - SLO Target), multi-window burn rates
(1h, 6h, 24h, 3d, 14d, 30d), Google SRE fast-burn / slow-burn alerting, and FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.slo import SLODefinition
from backend.app.services.slo import (
    DEFAULT_SLO_SPECS,
    SLOIntelligenceEngine,
)


# 1. Availability SLI calculation
def test_01_sli_availability_calculation():
    sli = SLOIntelligenceEngine.calculate_current_sli("order-service", "availability")
    assert 0.0 <= sli <= 100.0


# 2. Error rate SLI calculation
def test_02_sli_error_rate_calculation():
    from backend.app.services.observability.demo_mesh import demo_mesh
    demo_mesh.clear_all_faults()
    sli = SLOIntelligenceEngine.calculate_current_sli("api-gateway", "error_rate")
    assert 0.0 <= sli <= 100.0


# 3. Latency SLI within threshold
def test_03_sli_latency_within_threshold():
    # Latency threshold 500ms, actual p95 nominal ~50ms
    sli = SLOIntelligenceEngine.calculate_current_sli("order-service", "latency", threshold_value=500.0)
    assert sli >= 99.0


# 4. Latency SLI degraded over threshold
def test_04_sli_latency_degraded():
    # Latency threshold 10ms (artificially tiny so p95 ~ 100ms breaches threshold)
    sli = SLOIntelligenceEngine.calculate_current_sli("order-service", "latency", threshold_value=10.0)
    assert sli < 99.0


# 5. Full error budget remaining when SLI is 100%
def test_05_error_budget_full_remaining():
    res = SLOIntelligenceEngine.calculate_slo_result(
        slo_id="test-slo-1",
        service_name="order-service",
        name="Order Availability",
        slo_type="availability",
        target_percentage=99.9,
        override_sli=100.0,
    )
    assert res.error_budget_consumed_pct == 0.0
    assert res.error_budget_remaining_pct == 100.0
    assert res.status == "HEALTHY"


# 6. Budget status tier: HEALTHY (remaining >= 70%)
def test_06_budget_status_healthy():
    # Target 99.0% (allowed bad 1.0%), actual SLI 99.8% (actual bad 0.2% -> consumed 20%, remaining 80%)
    res = SLOIntelligenceEngine.calculate_slo_result(
        slo_id="test-slo-2",
        service_name="order-service",
        name="Order Latency",
        slo_type="latency",
        target_percentage=99.0,
        override_sli=99.8,
    )
    assert res.error_budget_remaining_pct == pytest.approx(80.0, 0.1)
    assert res.status == "HEALTHY"


# 7. Budget status tier: AT_RISK (30% <= remaining < 70%)
def test_07_budget_status_at_risk():
    # Target 99.0% (allowed bad 1.0%), actual SLI 99.5% (actual bad 0.5% -> consumed 50%, remaining 50%)
    res = SLOIntelligenceEngine.calculate_slo_result(
        slo_id="test-slo-3",
        service_name="payment-service",
        name="Payment Latency",
        slo_type="latency",
        target_percentage=99.0,
        override_sli=99.5,
    )
    assert res.error_budget_remaining_pct == pytest.approx(50.0, 0.1)
    assert res.status == "AT_RISK"


# 8. Budget status tier: CRITICAL (0% < remaining < 30%)
def test_08_budget_status_critical():
    # Target 99.0% (allowed bad 1.0%), actual SLI 99.15% (actual bad 0.85% -> consumed 85%, remaining 15%)
    res = SLOIntelligenceEngine.calculate_slo_result(
        slo_id="test-slo-4",
        service_name="auth-service",
        name="Auth Latency",
        slo_type="latency",
        target_percentage=99.0,
        override_sli=99.15,
    )
    assert res.error_budget_remaining_pct == pytest.approx(15.0, 0.1)
    assert res.status == "CRITICAL"


# 9. Budget status tier: EXHAUSTED (remaining <= 0%)
def test_09_budget_status_exhausted():
    # Target 99.9% (allowed bad 0.1%), actual SLI 99.5% (actual bad 0.5% -> consumed 500%, remaining 0%)
    res = SLOIntelligenceEngine.calculate_slo_result(
        slo_id="test-slo-5",
        service_name="order-service",
        name="Order Saturated",
        slo_type="availability",
        target_percentage=99.9,
        override_sli=99.5,
    )
    assert res.error_budget_consumed_pct >= 100.0
    assert res.error_budget_remaining_pct == 0.0
    assert res.status == "EXHAUSTED"


# 10. Burn rate calculation: 0.0 when zero bad events
def test_10_burn_rate_zero_when_perfect():
    report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="test-burn-1",
        service_name="order-service",
        slo_name="Order Perfect",
        target_percentage=99.9,
        current_sli=100.0,
    )
    assert report.current_burn_rate == 0.0
    assert not report.fast_burn_alert
    assert not report.slow_burn_alert
    assert report.alert_status == "OK"


# 11. Burn rate calculation: exactly 1.0 at target error consumption
def test_11_burn_rate_baseline_one():
    # Target 99.0% (allowed bad 1.0%), actual SLI 99.0% (actual bad 1.0% -> burn rate = 1.0)
    report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="test-burn-2",
        service_name="order-service",
        slo_name="Order Nominal",
        target_percentage=99.0,
        current_sli=99.0,
    )
    assert report.current_burn_rate == pytest.approx(1.0, 0.01)


# 12. Fast burn alert triggered (Burn rate > 14.4x)
def test_12_critical_fast_burn_alert():
    # Target 99.9% (allowed bad 0.1%), actual SLI 98.0% (actual bad 2.0% -> burn rate = 2.0 / 0.1 = 20.0x > 14.4x)
    report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="test-burn-3",
        service_name="payment-service",
        slo_name="Payment Fast Burn",
        target_percentage=99.9,
        current_sli=98.0,
    )
    assert report.current_burn_rate >= 14.4
    assert report.fast_burn_alert is True
    assert report.alert_status == "CRITICAL"


# 13. Slow burn alert triggered (1.0x < Burn rate < 6.0x)
def test_13_elevated_slow_burn_alert():
    # Target 99.9% (allowed bad 0.1%), actual SLI 99.75% (actual bad 0.25% -> burn rate = 0.25 / 0.1 = 2.5x)
    report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="test-burn-4",
        service_name="order-service",
        slo_name="Order Slow Burn",
        target_percentage=99.9,
        current_sli=99.75,
    )
    assert 1.0 < report.current_burn_rate < 6.0
    assert report.fast_burn_alert is False
    assert report.slow_burn_alert is True
    assert report.alert_status == "WARNING"


# 14. Multi-window evaluation
def test_14_multi_window_evaluation():
    report = SLOIntelligenceEngine.calculate_burn_rate_report(
        slo_id="test-burn-5",
        service_name="order-service",
        slo_name="Order Multi Window",
        target_percentage=99.9,
        current_sli=99.8,
    )
    window_names = [w.window_name for w in report.windows]
    assert "1h" in window_names
    assert "6h" in window_names
    assert "24h" in window_names
    assert "3d" in window_names
    assert "14d" in window_names
    assert "30d" in window_names


# 15. Database default SLO seeding
@pytest.mark.asyncio
async def test_15_ensure_default_slos_seeding(db_session: AsyncSession):
    created = await SLOIntelligenceEngine.ensure_default_slos(db_session)
    assert len(created) >= len(DEFAULT_SLO_SPECS)
    # Subsequent calls should return existing without duplicates
    second_call = await SLOIntelligenceEngine.ensure_default_slos(db_session)
    assert len(second_call) == len(created)


# 16. Error budgets query across services
@pytest.mark.asyncio
async def test_16_get_error_budgets_list(db_session: AsyncSession):
    budgets = await SLOIntelligenceEngine.get_error_budgets(db=db_session)
    assert len(budgets) >= 4
    for b in budgets:
        assert "target_percentage" in b
        assert "error_budget_remaining_pct" in b


# 17. Filter error budgets by service
@pytest.mark.asyncio
async def test_17_get_error_budgets_filtered(db_session: AsyncSession):
    budgets = await SLOIntelligenceEngine.get_error_budgets(service_name="order-service", db=db_session)
    assert len(budgets) >= 1
    for b in budgets:
        assert b["service_name"] == "order-service"


# 18. API: GET /api/v1/reliability/slo
@pytest.mark.asyncio
async def test_18_api_get_slos(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/slo")
    assert resp.status_code == 200
    data = resp.json()
    assert "slos" in data
    assert data["count"] >= 4


# 19. API: GET /api/v1/reliability/error-budget
@pytest.mark.asyncio
async def test_19_api_get_error_budget(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/error-budget?service_name=order-service")
    assert resp.status_code == 200
    data = resp.json()
    assert "error_budgets" in data
    assert data["service_name"] == "order-service"


# 20. API: GET /api/v1/reliability/burn-rate
@pytest.mark.asyncio
async def test_20_api_get_burn_rate(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/burn-rate")
    assert resp.status_code == 200
    data = resp.json()
    assert "burn_rates" in data
    assert data["count"] >= 4
    first_report = data["burn_rates"][0]
    assert "windows" in first_report
    assert "fast_burn_alert" in first_report
