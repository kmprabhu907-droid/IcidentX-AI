"""
INCIDENTX AI - SLO & Error Budget Intelligence Package (Stage 5.6)
Provides configurable SLO targets, error budget tracking, multi-window burn-rate analysis,
and Google SRE fast-burn / slow-burn alerting.
"""

from backend.app.services.slo.models import (
    BurnRateWindow,
    SLOBurnRateReport,
    SLOCalculationResult,
)
from backend.app.services.slo.engine import (
    DEFAULT_SLO_SPECS,
    SLOIntelligenceEngine,
)

__all__ = [
    "BurnRateWindow",
    "SLOBurnRateReport",
    "SLOCalculationResult",
    "DEFAULT_SLO_SPECS",
    "SLOIntelligenceEngine",
]
