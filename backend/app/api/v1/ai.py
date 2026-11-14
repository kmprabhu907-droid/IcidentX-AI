"""
INCIDENTX AI - AI Intelligence & Live Reasoning API Router (Phase 8.4)
Exposes endpoints for multi-provider health, live reasoning executions,
Root Cause Courtroom 2.0 verdicts, circuit breaker management, and cost/token tracking.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.services.ai.models import (
    AIIncidentReasoningReport,
    CourtroomVerdict,
    ProviderHealth,
)
from backend.app.services.ai.reasoning.reasoning_engine import reasoning_engine
from backend.app.services.ai.reasoning_memory import (
    HypothesisLifecycleState,
    reasoning_memory_bridge,
)
from backend.app.services.ai.router import llm_router
from backend.app.services.ai.usage_tracker import ai_usage_tracker

router = APIRouter(prefix="/ai", tags=["AI Reasoning & Multi-Provider Engine"])


class RunReasoningRequest(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None


class LifecycleUpdateRequest(BaseModel):
    hypothesis_id: str
    new_status: str
    reason: str = ""


@router.get("/providers")
async def get_providers() -> Dict[str, Any]:
    """
    List all supported LLM providers, their operational status, and active configuration.
    Never exposes raw API keys or secrets.
    """
    configured_providers = []

    for name, provider in llm_router.providers.items():
        is_primary = (name == getattr(settings, "AI_PROVIDER_PRIMARY", "gemini"))
        is_secondary = (name == getattr(settings, "AI_PROVIDER_SECONDARY", "openai"))
        is_fallback = (name == "deterministic")

        # Determine configured status without exposing keys
        if name == "gemini":
            configured = bool(getattr(settings, "GEMINI_API_KEY", None))
            default_model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        elif name == "openai":
            configured = bool(getattr(settings, "OPENAI_API_KEY", None))
            default_model = getattr(settings, "OPENAI_MODEL", "gpt-4o")
        elif name == "ollama":
            configured = True  # Local endpoint
            default_model = getattr(settings, "OLLAMA_MODEL", "llama3.1")
        elif name == "vllm":
            configured = True  # Self-hosted endpoint
            default_model = getattr(settings, "VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
        else:
            configured = True  # Deterministic is always available
            default_model = "incidentx-deterministic-v1"

        configured_providers.append({
            "provider_name": name,
            "display_name": provider.__class__.__name__,
            "configured": configured,
            "default_model": default_model,
            "is_primary": is_primary,
            "is_secondary": is_secondary,
            "is_fallback": is_fallback,
            "circuit_breaker_tripped": llm_router.circuit_breakers[name].is_tripped,
        })

    return {
        "active_primary_provider": getattr(settings, "AI_PROVIDER_PRIMARY", "gemini"),
        "active_secondary_provider": getattr(settings, "AI_PROVIDER_SECONDARY", "openai"),
        "fallback_provider": "deterministic",
        "providers": configured_providers,
    }


@router.get("/providers/health")
async def get_providers_health() -> Dict[str, Any]:
    """
    Run health checks against all configured LLM providers.
    Reports real latency and transparent connectivity status.
    """
    health_results = await llm_router.check_all_health()
    return {
        "status": "OK",
        "providers": {k: v.model_dump() for k, v in health_results.items()},
    }


@router.get("/models")
async def get_models() -> Dict[str, List[Dict[str, Any]]]:
    """
    List available models for each provider.
    """
    return {
        "gemini": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "tier": "Fast & Efficient"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "tier": "Deep Reasoning"},
        ],
        "openai": [
            {"id": "gpt-4o", "name": "GPT-4o", "tier": "Omni Flagship"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "tier": "Cost-Optimized"},
        ],
        "ollama": [
            {"id": getattr(settings, "OLLAMA_MODEL", "llama3.1"), "name": "Llama 3.1 (Local)", "tier": "Local Daemon"},
            {"id": "mistral", "name": "Mistral 7B (Local)", "tier": "Local Daemon"},
        ],
        "vllm": [
            {"id": getattr(settings, "VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"), "name": "vLLM Inference Cluster", "tier": "Self-Hosted"},
        ],
        "deterministic": [
            {"id": "incidentx-deterministic-v1", "name": "Deterministic Rule-Grounded Engine", "tier": "Zero-Dependency Fallback"},
        ],
    }


@router.get("/configuration")
async def get_ai_configuration() -> Dict[str, Any]:
    """
    Return sanitized AI configuration with no secrets exposed.
    """
    return {
        "primary_provider": getattr(settings, "AI_PROVIDER_PRIMARY", "gemini"),
        "secondary_provider": getattr(settings, "AI_PROVIDER_SECONDARY", "openai"),
        "gemini_model": getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash"),
        "gemini_configured": bool(getattr(settings, "GEMINI_API_KEY", None)),
        "openai_model": getattr(settings, "OPENAI_MODEL", "gpt-4o"),
        "openai_configured": bool(getattr(settings, "OPENAI_API_KEY", None)),
        "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
        "ollama_model": getattr(settings, "OLLAMA_MODEL", "llama3.1"),
        "vllm_base_url": getattr(settings, "VLLM_BASE_URL", "http://localhost:8000/v1"),
        "vllm_model": getattr(settings, "VLLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
        "daily_token_budget": getattr(settings, "AI_DAILY_TOKEN_BUDGET", 500000),
        "circuit_breaker_max_failures": getattr(settings, "AI_CIRCUIT_BREAKER_MAX_FAILURES", 3),
        "circuit_breaker_cooldown_seconds": getattr(settings, "AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60.0),
    }


@router.get("/usage")
async def get_ai_usage_summary() -> Dict[str, Any]:
    """
    Get aggregated token usage, cost expenditure ($), latency, and fallback counts.
    """
    return ai_usage_tracker.get_summary()


@router.get("/usage/{incident_id}")
async def get_incident_ai_usage(incident_id: str) -> Dict[str, Any]:
    """
    Get token consumption and cost details for a specific incident.
    """
    return ai_usage_tracker.get_incident_usage(incident_id)


@router.post("/reasoning/{incident_id}/run")
async def run_incident_reasoning(
    incident_id: str,
    payload: Optional[RunReasoningRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> AIIncidentReasoningReport:
    """
    Trigger end-to-end multi-agent AI reasoning for an incident.
    Grounds conclusions in verified telemetry, evaluates competing hypotheses in
    Courtroom 2.0, and records conclusions in the Reliability Memory Engine.
    """
    pref_prov = payload.preferred_provider if payload else None
    pref_model = payload.preferred_model if payload else None

    try:
        report = await reasoning_engine.run_reasoning(
            incident_id=incident_id,
            session=db,
            preferred_provider=pref_prov,
            preferred_model=pref_model,
        )
        return report
    except Exception as e:
        logger.error(f"[AIAPI] Error running reasoning for incident {incident_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reasoning engine failed: {str(e)}",
        )


@router.get("/reasoning/{incident_id}")
async def get_incident_reasoning(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve latest AI reasoning report for an incident.
    """
    report = reasoning_engine.get_report(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI reasoning report found for incident '{incident_id}'. Run reasoning first.",
        )
    return report.model_dump()


@router.get("/reasoning/{incident_id}/hypotheses")
async def get_reasoning_hypotheses(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve competing hypotheses and their courtroom status for an incident.
    """
    report = reasoning_engine.get_report(incident_id)
    if report:
        return {
            "incident_id": incident_id,
            "hypotheses": [h.model_dump() for h in report.courtroom_verdict.competing_hypotheses],
            "leading_hypothesis_id": report.courtroom_verdict.leading_hypothesis_id,
            "confidence_score": report.courtroom_verdict.confidence_score,
        }

    # Fallback to lifecycle state store
    lifecycle = await reasoning_memory_bridge.get_reasoning_lifecycle(incident_id)
    return lifecycle


@router.get("/reasoning/{incident_id}/courtroom")
async def get_courtroom_verdict(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve Courtroom 2.0 verdict, including counter-evidence checks and evidentiary justification.
    """
    report = reasoning_engine.get_report(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Courtroom verdict found for incident '{incident_id}'.",
        )
    return report.courtroom_verdict.model_dump()


@router.get("/reasoning/{incident_id}/evidence")
async def get_reasoning_evidence(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve normalized and validated evidence items considered in the reasoning session.
    """
    report = reasoning_engine.get_report(incident_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No reasoning evidence found for incident '{incident_id}'.",
        )
    return {
        "incident_id": incident_id,
        "evidence_count": len(report.evidence_items),
        "evidence_items": [e.model_dump() for e in report.evidence_items],
    }


@router.post("/reasoning/{incident_id}/hypotheses/lifecycle")
async def update_hypothesis_lifecycle(
    incident_id: str,
    payload: LifecycleUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Transition a hypothesis to a new lifecycle state (PROPOSED, INVESTIGATED, VERIFIED, REJECTED, SUPERSEDED).
    """
    try:
        updated = await reasoning_memory_bridge.update_hypothesis_lifecycle(
            incident_id=incident_id,
            hypothesis_id=payload.hypothesis_id,
            new_status=payload.new_status,
            reason=payload.reason,
            db=db,
        )
        return {
            "status": "SUCCESS" if updated else "NOT_FOUND",
            "incident_id": incident_id,
            "hypothesis_id": payload.hypothesis_id,
            "new_status": payload.new_status,
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get("/circuit-breaker")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """
    Check the circuit breaker status across all providers.
    """
    status_map = {}
    for name, cb in llm_router.circuit_breakers.items():
        status_map[name] = {
            "failure_count": cb.failure_count,
            "is_tripped": cb.is_tripped,
            "max_failures": cb.max_failures,
            "cooldown_seconds": cb.cooldown_seconds,
            "last_failure_time": cb.last_failure_time,
        }
    return {
        "status": "OK",
        "circuit_breakers": status_map,
    }


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(provider_name: Optional[str] = Query(None)) -> Dict[str, Any]:
    """
    Reset tripped circuit breakers for a specific provider or all providers.
    """
    if provider_name:
        if provider_name in llm_router.circuit_breakers:
            llm_router.circuit_breakers[provider_name].record_success()
            return {"status": "SUCCESS", "message": f"Circuit breaker for '{provider_name}' reset."}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider_name}' not found.",
            )
    else:
        for cb in llm_router.circuit_breakers.values():
            cb.record_success()
        return {"status": "SUCCESS", "message": "All circuit breakers reset."}
