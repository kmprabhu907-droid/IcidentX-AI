"""
INCIDENTX AI - SLO & Error Budget Models (Stage 5.6)
Defines calculation results, multi-window burn rates, and error budget statuses.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SLOCalculationResult(BaseModel):
    """Real-time calculation of an SLO target against current telemetry SLI."""
    slo_id: str
    service_name: str
    name: str
    slo_type: str  # availability, latency, error_rate
    target_percentage: float
    current_sli: float
    error_budget_total_pct: float
    error_budget_consumed_pct: float
    error_budget_remaining_pct: float
    status: str  # HEALTHY, AT_RISK, CRITICAL, EXHAUSTED
    window_days: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slo_id": self.slo_id,
            "service_name": self.service_name,
            "name": self.name,
            "slo_type": self.slo_type,
            "target_percentage": round(self.target_percentage, 3),
            "current_sli": round(self.current_sli, 3),
            "error_budget_total_pct": round(self.error_budget_total_pct, 4),
            "error_budget_consumed_pct": round(self.error_budget_consumed_pct, 2),
            "error_budget_remaining_pct": round(self.error_budget_remaining_pct, 2),
            "status": self.status,
            "window_days": self.window_days,
        }


class BurnRateWindow(BaseModel):
    """Burn rate measurement across a specific time evaluation window."""
    window_name: str  # 1h, 6h, 24h, 3d, 14d, 30d
    window_hours: float
    burn_rate: float
    budget_consumed_in_window_pct: float
    alert_tier: str  # NORMAL, ELEVATED_SLOW_BURN, HIGH_BURN, CRITICAL_FAST_BURN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_name": self.window_name,
            "window_hours": self.window_hours,
            "burn_rate": round(self.burn_rate, 2),
            "budget_consumed_in_window_pct": round(self.budget_consumed_in_window_pct, 2),
            "alert_tier": self.alert_tier,
        }


class SLOBurnRateReport(BaseModel):
    """Multi-window burn rate intelligence and Google SRE alert classification."""
    slo_id: str
    service_name: str
    slo_name: str
    current_burn_rate: float
    fast_burn_alert: bool  # Burn rate > 14.4x (consumes 2% in 1h or 5% in 6h)
    slow_burn_alert: bool  # Burn rate > 1.0x (consumes 100% before window ends)
    alert_status: str  # OK, WARNING, CRITICAL
    windows: List[BurnRateWindow] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slo_id": self.slo_id,
            "service_name": self.service_name,
            "slo_name": self.slo_name,
            "current_burn_rate": round(self.current_burn_rate, 2),
            "fast_burn_alert": self.fast_burn_alert,
            "slow_burn_alert": self.slow_burn_alert,
            "alert_status": self.alert_status,
            "windows": [w.to_dict() for w in self.windows],
        }
