"""
INCIDENTX AI - SLO & Error Budget Intelligence Engine
Computes Service Level Indicators (SLIs), remaining error budgets, multi-window burn rates,
and triggers Google SRE fast-burn and slow-burn alerts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.models.slo import SLODefinition, SLOMeasurement
from backend.app.services.observability.demo_mesh import demo_mesh
from backend.app.services.slo.models import (
    BurnRateWindow,
    SLOBurnRateReport,
    SLOCalculationResult,
)

DEFAULT_SLO_SPECS: List[Dict[str, Any]] = [
    {
        "service_name": "order-service",
        "name": "Order Service 30-Day Availability",
        "slo_type": "availability",
        "target_percentage": 99.9,
        "window_days": 30,
        "threshold_value": None,
    },
    {
        "service_name": "order-service",
        "name": "Order Service Latency Under 200ms",
        "slo_type": "latency",
        "target_percentage": 99.0,
        "window_days": 30,
        "threshold_value": 200.0,
    },
    {
        "service_name": "payment-service",
        "name": "Payment Service Availability",
        "slo_type": "availability",
        "target_percentage": 99.95,
        "window_days": 30,
        "threshold_value": None,
    },
    {
        "service_name": "api-gateway",
        "name": "API Gateway Low Error Rate",
        "slo_type": "error_rate",
        "target_percentage": 99.9,
        "window_days": 30,
        "threshold_value": None,
    },
    {
        "service_name": "auth-service",
        "name": "Auth Service Latency Under 150ms",
        "slo_type": "latency",
        "target_percentage": 99.5,
        "window_days": 30,
        "threshold_value": 150.0,
    },
    {
        "service_name": "postgres-db",
        "name": "Postgres Database Availability",
        "slo_type": "availability",
        "target_percentage": 99.99,
        "window_days": 30,
        "threshold_value": None,
    },
]


class SLOIntelligenceEngine:
    """
    Central intelligence engine for Stage 5.6.
    Evaluates real-time SLI metrics against SLO targets and calculates multi-window burn rates.
    """

    @classmethod
    async def ensure_default_slos(cls, db: AsyncSession) -> List[SLODefinition]:
        """
        Ensures baseline SLO definitions exist in the database.
        """
        stmt = select(SLODefinition)
        res = await db.execute(stmt)
        existing = res.scalars().all()
        if existing:
            return list(existing)

        created: List[SLODefinition] = []
        for spec in DEFAULT_SLO_SPECS:
            slo = SLODefinition(
                service_name=spec["service_name"],
                name=spec["name"],
                slo_type=spec["slo_type"],
                target_percentage=spec["target_percentage"],
                window_days=spec["window_days"],
                threshold_value=spec["threshold_value"],
                is_active=True,
            )
            db.add(slo)
            created.append(slo)

        await db.commit()
        return created

    @classmethod
    def calculate_current_sli(cls, service_name: str, slo_type: str, threshold_value: Optional[float] = None) -> float:
        """
        Extracts current SLI percentage from live demo_mesh metrics.
        """
        metrics = demo_mesh.get_latest_metrics().get(service_name, {})
        if not metrics:
            return 99.9

        if slo_type == "availability":
            return float(metrics.get("availability_pct", 99.95))

        elif slo_type == "error_rate":
            err_rate = float(metrics.get("error_rate", 0.001))
            # Handle both 0.0-1.0 fraction and 0.0-100.0 percentage representations
            err_pct = (err_rate * 100.0) if err_rate <= 1.0 else err_rate
            good_pct = max(0.0, min(100.0, 100.0 - err_pct))
            return good_pct

        elif slo_type == "latency":
            thresh = threshold_value or 200.0
            p95 = float(metrics.get("latency_p95_ms", 50.0))
            if p95 <= thresh:
                # Within target threshold
                headroom = 1.0 - (p95 / thresh)
                return min(100.0, 99.0 + (headroom * 1.0))
            else:
                # Over threshold: degrade SLI linearly
                overshoot = (p95 / thresh) - 1.0
                return max(50.0, 99.0 - (overshoot * 25.0))

        return 99.9

    @classmethod
    def calculate_slo_result(
        cls,
        slo_id: str,
        service_name: str,
        name: str,
        slo_type: str,
        target_percentage: float,
        window_days: int = 30,
        threshold_value: Optional[float] = None,
        override_sli: Optional[float] = None,
    ) -> SLOCalculationResult:
        """
        Computes remaining error budget and operational status.
        """
        current_sli = override_sli if override_sli is not None else cls.calculate_current_sli(service_name, slo_type, threshold_value)

        # Total allowed error percentage (e.g. 100 - 99.9 = 0.10%)
        allowed_error_pct = max(0.0001, 100.0 - target_percentage)

        # Actual observed bad percentage (e.g. 100 - 99.85 = 0.15%)
        actual_bad_pct = max(0.0, 100.0 - current_sli)

        # Error budget consumed percentage
        budget_consumed_pct = (actual_bad_pct / allowed_error_pct) * 100.0
        budget_remaining_pct = max(0.0, 100.0 - budget_consumed_pct)

        # Determine budget status tier
        if budget_remaining_pct <= 0.0:
            status = "EXHAUSTED"
        elif budget_remaining_pct < 30.0:
            status = "CRITICAL"
        elif budget_remaining_pct < 70.0:
            status = "AT_RISK"
        else:
            status = "HEALTHY"

        return SLOCalculationResult(
            slo_id=slo_id,
            service_name=service_name,
            name=name,
            slo_type=slo_type,
            target_percentage=target_percentage,
            current_sli=current_sli,
            error_budget_total_pct=allowed_error_pct,
            error_budget_consumed_pct=budget_consumed_pct,
            error_budget_remaining_pct=budget_remaining_pct,
            status=status,
            window_days=window_days,
        )

    @classmethod
    def calculate_burn_rate_report(
        cls,
        slo_id: str,
        service_name: str,
        slo_name: str,
        target_percentage: float,
        current_sli: float,
    ) -> SLOBurnRateReport:
        """
        Generates Google SRE multi-window burn-rate analysis and alert classifications.
        """
        allowed_bad_pct = max(0.0001, 100.0 - target_percentage)
        actual_bad_pct = max(0.0, 100.0 - current_sli)

        # Fundamental burn rate: 1.0 means consuming exactly 100% of budget over the full window
        base_burn_rate = actual_bad_pct / allowed_bad_pct if allowed_bad_pct > 0 else 0.0

        # Multi-window definitions (window_name, hours, multiplier_factor)
        window_configs = [
            ("1h", 1.0, 1.0),
            ("6h", 6.0, 0.95),
            ("24h", 24.0, 0.85),
            ("3d", 72.0, 0.70),
            ("14d", 336.0, 0.50),
            ("30d", 720.0, 0.35),
        ]

        windows: List[BurnRateWindow] = []
        fast_burn = False
        slow_burn = False

        for name, hours, dampener in window_configs:
            # Short windows reflect peak transient burn; long windows reflect smoothed baseline
            w_rate = max(0.0, base_burn_rate * (1.0 if name == "1h" else dampener))
            # Budget consumed in this window = (w_rate * hours) / 720h * 100
            budget_consumed = (w_rate * hours / 720.0) * 100.0

            if w_rate >= 14.4:
                tier = "CRITICAL_FAST_BURN"
                fast_burn = True
            elif w_rate >= 6.0:
                tier = "HIGH_BURN"
                fast_burn = True
            elif w_rate > 1.0:
                tier = "ELEVATED_SLOW_BURN"
                slow_burn = True
            else:
                tier = "NORMAL"

            windows.append(
                BurnRateWindow(
                    window_name=name,
                    window_hours=hours,
                    burn_rate=w_rate,
                    budget_consumed_in_window_pct=budget_consumed,
                    alert_tier=tier,
                )
            )

        if fast_burn:
            alert_status = "CRITICAL"
        elif slow_burn:
            alert_status = "WARNING"
        else:
            alert_status = "OK"

        return SLOBurnRateReport(
            slo_id=slo_id,
            service_name=service_name,
            slo_name=slo_name,
            current_burn_rate=base_burn_rate,
            fast_burn_alert=fast_burn,
            slow_burn_alert=slow_burn,
            alert_status=alert_status,
            windows=windows,
        )

    @classmethod
    async def get_all_slos_status(
        cls,
        service_name: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all active SLOs with current SLI, budget remaining, and status.
        """
        slos = []
        if db:
            slos = await cls.ensure_default_slos(db)
            if service_name:
                slos = [s for s in slos if s.service_name == service_name]
        else:
            specs = DEFAULT_SLO_SPECS
            if service_name:
                specs = [s for s in specs if s["service_name"] == service_name]
            for idx, sp in enumerate(specs):
                slos.append(
                    SLODefinition(
                        id=f"slo-spec-{idx}",
                        service_name=sp["service_name"],
                        name=sp["name"],
                        slo_type=sp["slo_type"],
                        target_percentage=sp["target_percentage"],
                        window_days=sp["window_days"],
                        threshold_value=sp["threshold_value"],
                        is_active=True,
                    )
                )

        results: List[Dict[str, Any]] = []
        for slo in slos:
            res = cls.calculate_slo_result(
                slo_id=slo.id,
                service_name=slo.service_name,
                name=slo.name,
                slo_type=slo.slo_type,
                target_percentage=slo.target_percentage,
                window_days=slo.window_days,
                threshold_value=slo.threshold_value,
            )
            results.append(res.to_dict())

        return results

    @classmethod
    async def get_error_budgets(
        cls,
        service_name: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detailed breakdown of error budget allocations, consumption, and burn status.
        """
        return await cls.get_all_slos_status(service_name=service_name, db=db)

    @classmethod
    async def get_burn_rates(
        cls,
        service_name: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates multi-window burn rates across all defined SLOs.
        """
        slo_statuses = await cls.get_all_slos_status(service_name=service_name, db=db)
        reports: List[Dict[str, Any]] = []

        for st in slo_statuses:
            report = cls.calculate_burn_rate_report(
                slo_id=st["slo_id"],
                service_name=st["service_name"],
                slo_name=st["name"],
                target_percentage=st["target_percentage"],
                current_sli=st["current_sli"],
            )
            reports.append(report.to_dict())

        return reports
