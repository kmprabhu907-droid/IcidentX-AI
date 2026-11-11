"""
INCIDENTX AI - Stage 5.5 Predictive Reliability Intelligence Tests
Validates trend models (OLS, EWMA), Time-to-Exhaustion (TTE = (Threshold - Current)/Growth Rate),
predictive warning generation, capacity risk scoring, and FastAPI predictive endpoints.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.reliability import PredictiveWarning
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.predictive import (
    DEFAULT_EXHAUSTION_THRESHOLDS,
    PredictiveReliabilityEngine,
    calculate_ewma_trend,
    calculate_ols_trend,
    calculate_tte,
    get_metric_threshold,
)


# 1. OLS linear regression calculation
def test_01_ols_trend_calculation():
    # Linear series: y = 2*x + 10
    series = [(0.0, 10.0), (10.0, 30.0), (20.0, 50.0), (30.0, 70.0)]
    slope, intercept, r_squared, std_err = calculate_ols_trend(series)
    assert slope == pytest.approx(2.0, 0.001)
    assert intercept == pytest.approx(10.0, 0.001)
    assert r_squared == pytest.approx(1.0, 0.001)


# 2. EWMA trend calculation
def test_02_ewma_trend_calculation():
    series = [(0.0, 10.0), (1.0, 12.0), (2.0, 14.0), (3.0, 16.0)]
    ewma_slope = calculate_ewma_trend(series, alpha=0.3)
    assert ewma_slope == pytest.approx(2.0, 0.01)


# 3. Time-to-Exhaustion positive growth calculation
def test_03_calculate_tte_positive_growth():
    # Current 50%, Threshold 90%, Growth 2%/sec -> TTE = (90 - 50) / 2 = 20 seconds
    tte = calculate_tte(current_value=50.0, threshold=90.0, growth_rate_per_sec=2.0)
    assert tte == pytest.approx(20.0, 0.01)


# 4. Time-to-Exhaustion when already breached
def test_04_calculate_tte_already_exhausted():
    tte = calculate_tte(current_value=95.0, threshold=90.0, growth_rate_per_sec=1.5)
    assert tte == 0.0


# 5. Time-to-Exhaustion when flat or decreasing
def test_05_calculate_tte_flat_or_decreasing():
    assert calculate_tte(current_value=40.0, threshold=90.0, growth_rate_per_sec=0.0) is None
    assert calculate_tte(current_value=40.0, threshold=90.0, growth_rate_per_sec=-0.5) is None


# 6. Default exhaustion thresholds lookup
def test_06_exhaustion_threshold_lookup():
    assert get_metric_threshold("db_pool_utilization") == 95.0
    assert get_metric_threshold("memory_utilization") == 90.0
    assert get_metric_threshold("latency_p95_ms") == 1000.0
    assert get_metric_threshold("unknown_custom_metric") == 90.0


# 7. Metric series evaluation and ResourcePrediction model
def test_07_evaluate_metric_series():
    t0 = 1000.0
    # Simulate DB connection leak growing by 0.5% every second
    series = [(t0 + i, 20.0 + (0.5 * i)) for i in range(60)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="order-service",
        metric_name="db_pool_utilization",
        time_series=series,
    )
    assert pred.service_name == "order-service"
    assert pred.metric_name == "db_pool_utilization"
    assert pred.current_value == pytest.approx(49.5, 0.5)
    assert pred.growth_rate_per_sec == pytest.approx(0.5, 0.05)
    assert pred.time_to_exhaustion_seconds is not None
    # Remaining capacity: 95.0 - 49.5 = 45.5 / 0.5 ~ 91 seconds -> CRITICAL (< 300s)
    assert pred.warning_level == "CRITICAL"
    assert len(pred.forecast_points) >= 5


# 8. Forecast points with expanding confidence bounds
def test_08_forecast_points_expanding_intervals():
    t0 = 2000.0
    series = [(t0 + i, 30.0 + (0.1 * i)) for i in range(30)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="auth-service",
        metric_name="memory_utilization",
        time_series=series,
    )
    assert len(pred.forecast_points) >= 3
    # Check that upper bound is strictly greater than lower bound and predicted value is bounded
    for pt in pred.forecast_points:
        assert pt.lower_bound <= pt.predicted_value <= pt.upper_bound


# 9. Warning level classification: WARNING tier
def test_09_warning_level_warning_tier():
    t0 = 1000.0
    # Slow growth: from 50 to 52 over 60 seconds (rate ~ 0.033/sec, remaining to 90 is 38 -> TTE ~ 1150s (19m) -> WARNING)
    series = [(t0 + i, 50.0 + (0.0333 * i)) for i in range(60)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="inventory-service",
        metric_name="memory_utilization",
        time_series=series,
    )
    assert pred.warning_level == "WARNING"


# 10. Warning level classification: NOMINAL tier
def test_10_warning_level_nominal_tier():
    t0 = 1000.0
    # Decreasing or perfectly flat metric
    series = [(t0 + i, 25.0) for i in range(60)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="payment-service",
        metric_name="cpu_utilization",
        time_series=series,
    )
    assert pred.warning_level == "NOMINAL"
    assert pred.time_to_exhaustion_seconds is None


# 11. Predictive warning DB persistence
@pytest.mark.asyncio
async def test_11_persist_warning_if_needed(db_session: AsyncSession):
    t0 = 1000.0
    series = [(t0 + i, 70.0 + (0.4 * i)) for i in range(50)]
    pred = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="order-service",
        metric_name="db_pool_utilization",
        time_series=series,
    )
    assert pred.warning_level == "CRITICAL"

    warning = await PredictiveReliabilityEngine.persist_warning_if_needed(pred, db_session)
    assert warning is not None
    assert warning.service_name == "order-service"
    assert "DB_POOL_UTILIZATION_EXHAUSTION" in warning.warning_type
    assert warning.impact_level == "CRITICAL"


# 12. Predictive warning update without duplicate spam
@pytest.mark.asyncio
async def test_12_persist_warning_updates_existing(db_session: AsyncSession):
    t0 = 1000.0
    series1 = [(t0 + i, 70.0 + (0.3 * i)) for i in range(30)]
    pred1 = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="order-service",
        metric_name="db_pool_utilization",
        time_series=series1,
    )
    w1 = await PredictiveReliabilityEngine.persist_warning_if_needed(pred1, db_session)
    assert w1 is not None

    # Follow-up analysis updates existing active unacknowledged warning
    series2 = [(t0 + i, 79.0 + (0.3 * i)) for i in range(30)]
    pred2 = PredictiveReliabilityEngine.evaluate_metric_series(
        service_name="order-service",
        metric_name="db_pool_utilization",
        time_series=series2,
    )
    w2 = await PredictiveReliabilityEngine.persist_warning_if_needed(pred2, db_session)
    assert w2.id == w1.id

    # Verify count in DB remains 1
    stmt = select(PredictiveWarning).where(PredictiveWarning.service_name == "order-service")
    res = await db_session.execute(stmt)
    assert len(res.scalars().all()) == 1


# 13. End-to-end service analysis from live demo_mesh
@pytest.mark.asyncio
async def test_13_analyze_service_streaming():
    preds = await PredictiveReliabilityEngine.analyze_service("order-service", window_seconds=60)
    assert len(preds) >= 4
    metrics = [p.metric_name for p in preds]
    assert "db_pool_utilization" in metrics
    assert "cpu_utilization" in metrics


# 14. Cluster-wide capacity risk scoring
@pytest.mark.asyncio
async def test_14_capacity_risks_cluster():
    risks = await PredictiveReliabilityEngine.get_capacity_risks()
    assert len(risks) >= 5
    # Should be sorted descending by overall_risk_score
    scores = [r["overall_risk_score"] for r in risks]
    assert scores == sorted(scores, reverse=True)


# 15. Prescriptive SRE recommendations
@pytest.mark.asyncio
async def test_15_prescriptive_recommendations():
    risks = await PredictiveReliabilityEngine.get_capacity_risks()
    for r in risks:
        assert "recommendations" in r
        assert len(r["recommendations"]) >= 1


# 16. Service forecast generation
@pytest.mark.asyncio
async def test_16_service_forecast():
    fc = await PredictiveReliabilityEngine.get_service_forecast("order-service", metric_name="memory_utilization")
    assert fc["service_name"] == "order-service"
    assert fc["metric_name"] == "memory_utilization"
    assert "forecast_points" in fc


# 17. API: GET /api/v1/reliability/predictions
@pytest.mark.asyncio
async def test_17_api_get_predictions(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data
    assert data["count"] >= 1


# 18. API: GET /api/v1/reliability/predictions with service filter
@pytest.mark.asyncio
async def test_18_api_get_predictions_filtered(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/predictions?service_name=order-service")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "order-service"
    for p in data["predictions"]:
        assert p["service_name"] == "order-service"


# 19. API: GET /api/v1/reliability/forecast/{service_id}
@pytest.mark.asyncio
async def test_19_api_get_forecast(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/forecast/order-service?metric_name=cpu_utilization")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_name"] == "order-service"
    assert data["metric_name"] == "cpu_utilization"
    assert len(data["forecast_points"]) >= 1


# 20. API: GET /api/v1/reliability/capacity-risk
@pytest.mark.asyncio
async def test_20_api_get_capacity_risk(client: AsyncClient):
    resp = await client.get("/api/v1/reliability/capacity-risk")
    assert resp.status_code == 200
    data = resp.json()
    assert "risks" in data
    assert data["count"] >= 5
    assert "risk_tier" in data["risks"][0]
