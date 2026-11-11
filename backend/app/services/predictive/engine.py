"""
INCIDENTX AI - Predictive Reliability Engine
Analyzes streaming and rollup telemetry, computes growth slopes, projects
Time-to-Exhaustion (TTE), emits predictive warnings, and synthesizes capacity risk tiers.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.reliability import PredictiveWarning
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.predictive.models import (
    CapacityRiskSummary,
    ForecastPoint,
    ResourcePrediction,
)
from backend.app.services.predictive.trend_models import (
    calculate_ewma_trend,
    calculate_ols_trend,
    calculate_tte,
    get_metric_threshold,
)

TRACKED_PREDICTIVE_METRICS = [
    "db_pool_utilization",
    "memory_utilization",
    "cpu_utilization",
    "disk_utilization",
    "latency_p95_ms",
    "error_rate",
]


class PredictiveReliabilityEngine:
    """
    Central intelligence engine for Stage 5.5.
    Detects resource degradation before incidents occur.
    """

    @classmethod
    def evaluate_metric_series(
        cls,
        service_name: str,
        metric_name: str,
        time_series: List[Tuple[float, float]],
        current_value: Optional[float] = None,
        forecast_horizon_seconds: int = 1800,
    ) -> ResourcePrediction:
        """
        Evaluates trend and projects exhaustion for a specific metric time-series.
        time_series format: List of (timestamp_epoch_seconds, metric_value).
        """
        threshold = get_metric_threshold(metric_name)

        if not time_series:
            curr = current_value or 0.0
            return ResourcePrediction(
                service_name=service_name,
                metric_name=metric_name,
                current_value=curr,
                growth_rate_per_sec=0.0,
                growth_rate_per_min=0.0,
                exhaustion_threshold=threshold,
                time_to_exhaustion_seconds=None,
                time_to_exhaustion_minutes=None,
                r_squared=0.0,
                warning_level="NOMINAL",
                trend_model="LINEAR_OLS",
                sample_count=0,
                forecast_points=[],
            )

        # Sort chronologically
        sorted_series = sorted(time_series, key=lambda x: x[0])
        curr_val = current_value if current_value is not None else sorted_series[-1][1]

        # Calculate OLS & EWMA trends
        ols_slope, ols_intercept, r_squared, std_err = calculate_ols_trend(sorted_series)
        ewma_slope = calculate_ewma_trend(sorted_series, alpha=0.25)

        # Growth rate per second: combine OLS and EWMA when both agree on positive trend
        if ols_slope > 0 and ewma_slope > 0:
            effective_growth_rate = 0.6 * ols_slope + 0.4 * ewma_slope
            model_type = "HYBRID_OLS_EWMA"
        elif ols_slope > 0:
            effective_growth_rate = ols_slope
            model_type = "LINEAR_OLS"
        elif ewma_slope > 0:
            effective_growth_rate = ewma_slope
            model_type = "EWMA_MOMENTUM"
        else:
            effective_growth_rate = min(ols_slope, ewma_slope)
            model_type = "LINEAR_OLS"

        growth_per_min = effective_growth_rate * 60.0

        # Compute Time to Exhaustion (TTE = (Threshold - Current) / Growth Rate)
        tte_seconds = calculate_tte(curr_val, threshold, effective_growth_rate)
        tte_minutes = (tte_seconds / 60.0) if tte_seconds is not None else None

        # Determine warning level
        if curr_val >= threshold or (tte_seconds is not None and tte_seconds <= 300.0):
            warning_level = "CRITICAL"
        elif tte_seconds is not None and tte_seconds <= 1800.0 and (r_squared >= 0.35 or effective_growth_rate > 0.05):
            warning_level = "WARNING"
        elif tte_seconds is not None and tte_seconds <= 7200.0:
            warning_level = "ADVISORY"
        else:
            warning_level = "NOMINAL"

        # Generate forecast points
        forecast_points: List[ForecastPoint] = []
        base_t = sorted_series[-1][0]
        intervals_minutes = [1.0, 5.0, 10.0, 15.0, 20.0, 30.0]

        for m in intervals_minutes:
            future_sec = base_t + (m * 60.0)
            proj_val = curr_val + (effective_growth_rate * m * 60.0)
            # Confidence interval margin expands with time: std_err * sqrt(1 + m/5.0) * 1.96
            margin = max(1.0, (std_err or 1.5) * (1.0 + (m / 10.0)))
            dt_iso = datetime.fromtimestamp(future_sec, tz=timezone.utc).isoformat()
            forecast_points.append(
                ForecastPoint(
                    timestamp=dt_iso,
                    minutes_ahead=m,
                    predicted_value=max(0.0, proj_val),
                    lower_bound=max(0.0, proj_val - margin),
                    upper_bound=proj_val + margin,
                )
            )

        return ResourcePrediction(
            service_name=service_name,
            metric_name=metric_name,
            current_value=curr_val,
            growth_rate_per_sec=effective_growth_rate,
            growth_rate_per_min=growth_per_min,
            exhaustion_threshold=threshold,
            time_to_exhaustion_seconds=tte_seconds,
            time_to_exhaustion_minutes=tte_minutes,
            r_squared=r_squared,
            warning_level=warning_level,
            trend_model=model_type,
            sample_count=len(sorted_series),
            forecast_points=forecast_points,
        )

    @classmethod
    async def analyze_service(
        cls,
        service_name: str,
        window_seconds: int = 120,
        db: Optional[AsyncSession] = None,
    ) -> List[ResourcePrediction]:
        """
        Analyzes streaming time series for a service and optionally emits PredictiveWarning records.
        """
        history = demo_mesh.get_service_history(service_name, seconds=window_seconds)
        predictions: List[ResourcePrediction] = []

        for metric in TRACKED_PREDICTIVE_METRICS:
            series: List[Tuple[float, float]] = []
            for item in history:
                if metric in item and item[metric] is not None:
                    try:
                        ts = datetime.fromisoformat(item["timestamp"]).timestamp()
                        val = float(item[metric])
                        series.append((ts, val))
                    except (ValueError, TypeError):
                        continue

            pred = cls.evaluate_metric_series(
                service_name=service_name,
                metric_name=metric,
                time_series=series,
            )
            predictions.append(pred)

            # Persist warning if threshold hazard detected and db is available
            if db and pred.warning_level in ["WARNING", "CRITICAL"]:
                await cls.persist_warning_if_needed(pred, db)

        return predictions

    @classmethod
    async def persist_warning_if_needed(
        cls,
        pred: ResourcePrediction,
        db: AsyncSession,
    ) -> Optional[PredictiveWarning]:
        """
        Saves or updates an active PredictiveWarning for an impending exhaustion event.
        """
        try:
            # Check if active unacknowledged warning already exists
            stmt = (
                select(PredictiveWarning)
                .where(
                    PredictiveWarning.service_name == pred.service_name,
                    PredictiveWarning.warning_type == f"{pred.metric_name.upper()}_EXHAUSTION",
                    PredictiveWarning.acknowledged == False,  # noqa: E712
                )
                .order_by(desc(PredictiveWarning.emitted_at))
                .limit(1)
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()

            msg = (
                f"Projected {pred.metric_name} exhaustion on {pred.service_name}: "
                f"current {pred.current_value:.1f} approaching {pred.exhaustion_threshold:.1f} "
                f"(growth: {pred.growth_rate_per_min:+.2f}/min, TTE: {pred.time_to_exhaustion_minutes:.1f}m)."
            )

            if existing:
                existing.projected_time_to_exhaustion_seconds = pred.time_to_exhaustion_seconds
                existing.message = msg
                existing.confidence = max(0.80, pred.r_squared)
                existing.impact_level = "CRITICAL" if pred.warning_level == "CRITICAL" else "HIGH"
                await db.commit()
                return existing

            warning = PredictiveWarning(
                service_name=pred.service_name,
                warning_type=f"{pred.metric_name.upper()}_EXHAUSTION",
                message=msg,
                confidence=max(0.80, pred.r_squared),
                projected_time_to_exhaustion_seconds=pred.time_to_exhaustion_seconds,
                impact_level="CRITICAL" if pred.warning_level == "CRITICAL" else "HIGH",
                supporting_evidence=f"OLS R^2: {pred.r_squared:.2f}, Growth: {pred.growth_rate_per_min:.3f}/min",
                relevant_time_window="15m",
                acknowledged=False,
            )
            db.add(warning)
            await db.commit()
            return warning
        except Exception as e:
            logger.warning(f"Failed to persist predictive warning: {e}")
            await db.rollback()
            return None

    @classmethod
    async def get_active_predictions(
        cls,
        service_name: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves active predictions across specified service or all simulated topology nodes.
        """
        services = [service_name] if service_name else list(demo_mesh.SERVICE_DEFINITIONS.keys())
        all_preds: List[Dict[str, Any]] = []

        for svc in services:
            svc_preds = await cls.analyze_service(svc, window_seconds=120, db=db)
            all_preds.extend([p.to_dict() for p in svc_preds])

        return all_preds

    @classmethod
    async def get_service_forecast(
        cls,
        service_name: str,
        metric_name: Optional[str] = None,
        horizon_seconds: int = 1800,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Generates forward-looking forecast points and confidence bounds for a service.
        """
        preds = await cls.analyze_service(service_name, window_seconds=180, db=db)

        if metric_name:
            filtered = [p for p in preds if p.metric_name == metric_name]
            target_pred = filtered[0] if filtered else None
        else:
            # Pick highest risk metric
            target_pred = min(
                preds,
                key=lambda p: p.time_to_exhaustion_seconds if p.time_to_exhaustion_seconds is not None else 999999.0
            )

        if not target_pred:
            target_pred = preds[0] if preds else None

        return {
            "service_name": service_name,
            "metric_name": target_pred.metric_name if target_pred else "unknown",
            "current_value": target_pred.current_value if target_pred else 0.0,
            "growth_rate_per_min": target_pred.growth_rate_per_min if target_pred else 0.0,
            "time_to_exhaustion_minutes": target_pred.time_to_exhaustion_minutes if target_pred else None,
            "warning_level": target_pred.warning_level if target_pred else "NOMINAL",
            "forecast_horizon_seconds": horizon_seconds,
            "forecast_points": [p.to_dict() for p in (target_pred.forecast_points if target_pred else [])],
            "all_metric_predictions": [p.to_dict() for p in preds],
        }

    @classmethod
    async def get_capacity_risks(
        cls,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregates capacity risks across all services, sorted descending by hazard severity,
        complete with prescriptive SRE prevention recommendations.
        """
        services = list(demo_mesh.SERVICE_DEFINITIONS.keys())
        summaries: List[CapacityRiskSummary] = []

        for svc in services:
            preds = await cls.analyze_service(svc, window_seconds=120, db=db)
            if not preds:
                continue

            # Identify metric with shortest TTE
            exhaustion_candidates = [p for p in preds if p.time_to_exhaustion_seconds is not None]
            if exhaustion_candidates:
                critical_pred = min(exhaustion_candidates, key=lambda p: p.time_to_exhaustion_seconds)
                shortest_tte = critical_pred.time_to_exhaustion_seconds
                shortest_tte_min = critical_pred.time_to_exhaustion_minutes
                highest_metric = critical_pred.metric_name
                highest_val = critical_pred.current_value
            else:
                # Fallback to metric closest to threshold percentage
                critical_pred = max(preds, key=lambda p: (p.current_value / p.exhaustion_threshold))
                shortest_tte = None
                shortest_tte_min = None
                highest_metric = critical_pred.metric_name
                highest_val = critical_pred.current_value

            # Calculate overall risk score (0 to 100)
            if shortest_tte is not None:
                if shortest_tte <= 300.0:
                    score = 95.0
                    tier = "CRITICAL"
                elif shortest_tte <= 900.0:
                    score = 80.0
                    tier = "HIGH"
                elif shortest_tte <= 1800.0:
                    score = 65.0
                    tier = "MODERATE"
                elif shortest_tte <= 7200.0:
                    score = 40.0
                    tier = "LOW"
                else:
                    score = 15.0
                    tier = "HEALTHY"
            else:
                score = min(35.0, (highest_val / critical_pred.exhaustion_threshold) * 35.0)
                tier = "HEALTHY" if score < 25.0 else "LOW"

            # Formulate prescriptive SRE recommendations
            recommendations: List[str] = []
            if highest_metric == "db_pool_utilization":
                recommendations.append("Cycle idle pool connections or increase max_connections limit.")
                recommendations.append("Audit connection leak patterns in unclosed database sessions.")
            elif highest_metric == "memory_utilization":
                recommendations.append("Initiate heap memory profiling and monitor GC pauses.")
                recommendations.append("Prepare container memory limit scaling if creep continues.")
            elif highest_metric == "cpu_utilization":
                recommendations.append("Trigger proactive Horizontal Pod Autoscaling (HPA).")
            elif highest_metric == "disk_utilization":
                recommendations.append("Trigger automated log directory rotation and volume expansion.")
            elif highest_metric == "error_rate":
                recommendations.append("Throttle ingress traffic or activate upstream circuit breaker.")
            else:
                recommendations.append("Continuously monitor latency percentiles and upstream dependencies.")

            summaries.append(
                CapacityRiskSummary(
                    service_name=svc,
                    highest_risk_metric=highest_metric,
                    current_metric_value=highest_val,
                    shortest_tte_seconds=shortest_tte,
                    shortest_tte_minutes=shortest_tte_min,
                    overall_risk_score=score,
                    risk_tier=tier,
                    recommendations=recommendations,
                )
            )

        # Sort descending by overall risk score
        summaries.sort(key=lambda s: s.overall_risk_score, reverse=True)
        return [s.to_dict() for s in summaries]
