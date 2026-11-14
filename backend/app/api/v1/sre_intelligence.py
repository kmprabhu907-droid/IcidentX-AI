"""
INCIDENTX AI - Advanced SRE Intelligence API Endpoints (Phase 15)
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.app.services.sre_intelligence.sre_engine import sre_intelligence_engine
from backend.app.services.sre_intelligence.schemas import (
    CascadingFailureRisk,
    DeploymentRiskAssessment,
    ModelEvaluationMetrics,
    MultiSignalAnomalyReport,
    PredictedIncidentRisk,
    PredictiveRecommendation,
    SLOTarget,
    ServiceHealthOverview,
)

router = APIRouter(prefix="/sre-intelligence", tags=["Predictive SRE Intelligence (Phase 15)"])


@router.get("/anomalies", response_model=MultiSignalAnomalyReport)
async def get_anomalies(
    service: str = Query("payment-service"),
    cpu: Optional[float] = Query(None),
    memory: Optional[float] = Query(None),
    p95_latency: Optional[float] = Query(None),
    error_rate: Optional[float] = Query(None),
):
    metrics = {
        "cpu_percent": cpu,
        "memory_percent": memory,
        "p95_latency_ms": p95_latency,
        "error_rate_percent": error_rate,
    }
    return sre_intelligence_engine.detect_anomalies(service, metrics)


@router.get("/predictions", response_model=List[PredictedIncidentRisk])
async def get_predictions(
    service: str = Query("payment-service"),
    memory: Optional[float] = Query(None),
    cpu: Optional[float] = Query(None),
    p95_latency: Optional[float] = Query(None),
    error_rate: Optional[float] = Query(None),
):
    metrics = {
        "memory_percent": memory,
        "cpu_percent": cpu,
        "p95_latency_ms": p95_latency,
        "error_rate_percent": error_rate,
    }
    return sre_intelligence_engine.predict_incidents(service, metrics)


@router.get("/health", response_model=ServiceHealthOverview)
async def get_service_health(
    service: str = Query("payment-service"),
    error_rate: Optional[float] = Query(None),
    p95_latency: Optional[float] = Query(None),
):
    metrics = {
        "error_rate_percent": error_rate,
        "p95_latency_ms": p95_latency,
    }
    return sre_intelligence_engine.evaluate_service_health(service, metrics)


@router.get("/slos", response_model=List[SLOTarget])
async def get_slos(
    service: str = Query("payment-service"),
    error_rate: float = Query(0.02),
):
    return sre_intelligence_engine.get_slo_targets(service, error_rate)


@router.get("/deployments/correlate", response_model=DeploymentRiskAssessment)
async def correlate_deployment(
    service: str = Query("payment-service"),
    git_sha: str = Query("sha-9b2f11"),
    error_rate: float = Query(0.05),
):
    return sre_intelligence_engine.correlate_deployment(service, git_sha=git_sha, error_rate=error_rate)


@router.get("/cascading", response_model=CascadingFailureRisk)
async def get_cascading_risk(service: str = Query("payment-service")):
    return sre_intelligence_engine.evaluate_cascading_risk(service)


@router.get("/recommendations", response_model=List[PredictiveRecommendation])
async def get_proactive_recommendations(service: str = Query("payment-service")):
    predictions = sre_intelligence_engine.predict_incidents(service, {})
    return sre_intelligence_engine.get_proactive_recommendations(service, predictions)


@router.get("/evaluation", response_model=ModelEvaluationMetrics)
async def get_evaluation():
    return sre_intelligence_engine.get_model_evaluation()
