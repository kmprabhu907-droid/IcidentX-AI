"""
INCIDENTX AI - Stage 5.3 Regression Detection Package
"""

from backend.app.services.observability.regression.comparison_engine import (
    FourStateComparison,
    FourStateComparisonEngine,
    MetricStateValue,
    SIGNAL_SPECIFICATIONS,
)
from backend.app.services.observability.regression.fingerprint import (
    FingerprintBuilder,
    IncidentFingerprint,
    normalize_error_string,
)
from backend.app.services.observability.regression.regression_detector import (
    RegressionCandidate,
    UnifiedRegressionDetector,
)
from backend.app.services.observability.regression.regression_explainer import (
    SRERegressionExplainer,
    SRERegressionExplanation,
)
from backend.app.services.observability.regression.regression_service import (
    RegressionLifecycleService,
)
from backend.app.services.observability.regression.remediation_effectiveness import (
    RemediationEffectivenessAnalyzer,
    RemediationEffectivenessReport,
)
from backend.app.services.observability.regression.reliability_memory import (
    ReliabilityMemoryInterface,
    SqlAlchemyReliabilityMemory,
)
from backend.app.services.observability.regression.similarity import (
    IncidentSimilarityEngine,
    SimilarityResult,
)

__all__ = [
    "FourStateComparison",
    "FourStateComparisonEngine",
    "MetricStateValue",
    "SIGNAL_SPECIFICATIONS",
    "FingerprintBuilder",
    "IncidentFingerprint",
    "normalize_error_string",
    "IncidentSimilarityEngine",
    "SimilarityResult",
    "RemediationEffectivenessAnalyzer",
    "RemediationEffectivenessReport",
    "SRERegressionExplainer",
    "SRERegressionExplanation",
    "ReliabilityMemoryInterface",
    "SqlAlchemyReliabilityMemory",
    "RegressionCandidate",
    "UnifiedRegressionDetector",
    "RegressionLifecycleService",
]
