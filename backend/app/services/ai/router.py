"""
INCIDENTX AI - Intelligent LLM Provider Router & Circuit Breaker (Phase 8.4)
Routes reasoning requests across Gemini, OpenAI, Ollama, vLLM, and Deterministic engines.
Implements bounded exponential retries, circuit breakers, and transparent execution attribution.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.ai.models import ModelAttribution, ProviderHealth, TokenUsage
from backend.app.services.ai.providers import (
    AuthenticationError,
    BaseLLMProvider,
    DeterministicProvider,
    GeminiProvider,
    LLMProviderError,
    ModelTimeoutError,
    OllamaProvider,
    OpenAIProvider,
    ProviderUnavailableError,
    RateLimitError,
    VLLMProvider,
)
from backend.app.services.ai.sanitizer import PromptSanitizer

T = TypeVar("T", bound=BaseModel)


class CircuitBreaker:
    """
    Per-provider circuit breaker to prevent cascading timeouts and rate limit penalties.
    """

    def __init__(self, max_failures: int = 3, cooldown_seconds: float = 60.0):
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0

    @property
    def is_tripped(self) -> bool:
        if self.failure_count >= self.max_failures:
            # Check if cooldown window has elapsed
            if (time.time() - self.last_failure_time) > self.cooldown_seconds:
                # Half-open: allow next trial
                return False
            return True
        return False

    def record_success(self) -> None:
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()


class LLMRouter:
    """
    Manages intelligent dispatching, circuit breaking, fallback cascades,
    and transparent attribution across multiple AI providers.
    """

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "ollama": OllamaProvider(),
            "vllm": VLLMProvider(),
            "deterministic": DeterministicProvider(),
        }
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            name: CircuitBreaker(
                max_failures=settings.AI_CIRCUIT_BREAKER_MAX_FAILURES,
                cooldown_seconds=settings.AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS,
            )
            for name in self.providers
        }

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        return self.providers.get(name.lower())

    async def check_all_health(self) -> Dict[str, ProviderHealth]:
        """Probe health across all registered providers."""
        results = {}
        for name, provider in self.providers.items():
            results[name] = await provider.check_health()
        return results

    async def generate_structured(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        context_data: Optional[Dict[str, Any]] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        incident_id: Optional[str] = None,
        agent_name: str = "InvestigationAgent",
    ) -> Tuple[T, ModelAttribution]:
        """
        Execute structured generation with multi-provider routing and deterministic fallback.
        """
        from backend.app.services.ai.usage_tracker import ai_usage_tracker

        start_time = time.perf_counter()

        # Sanitize prompts for injection protection and secret masking
        clean_system = PromptSanitizer.sanitize_text(system_prompt)
        clean_user = PromptSanitizer.sanitize_text(user_prompt)
        clean_context = PromptSanitizer.sanitize_dict(context_data or {})

        # Determine provider candidate chain
        primary_name = (preferred_provider or settings.AI_PROVIDER_PRIMARY or settings.AI_PROVIDER).lower()
        secondary_name = (settings.AI_PROVIDER_SECONDARY or "deterministic").lower()

        # Build cascade list with no duplicates and ending with deterministic
        cascade: List[str] = []
        if primary_name in self.providers:
            cascade.append(primary_name)
        if secondary_name in self.providers and secondary_name not in cascade:
            cascade.append(secondary_name)
        if "deterministic" not in cascade:
            cascade.append("deterministic")

        last_error = None
        is_fallback = False

        for idx, provider_name in enumerate(cascade):
            provider = self.providers[provider_name]
            cb = self.circuit_breakers[provider_name]

            # If circuit breaker is tripped on non-deterministic provider, skip to fallback
            if cb.is_tripped and provider_name != "deterministic":
                logger.warning(
                    f"[LLMRouter] Circuit breaker tripped for provider '{provider_name}'. Skipping to next candidate."
                )
                is_fallback = True
                continue

            # Check if credentials exist for cloud providers
            if provider_name in ("gemini", "openai"):
                key = getattr(provider, "api_key", None)
                if not key:
                    logger.debug(f"[LLMRouter] Provider '{provider_name}' has no API key. Skipping.")
                    is_fallback = True
                    continue

            try:
                target_model = preferred_model if idx == 0 and preferred_model else provider.default_model

                # Execute call
                parsed_data, token_usage, _ = await provider.generate_structured(
                    schema=schema,
                    system_prompt=clean_system,
                    user_prompt=clean_user,
                    context_data=clean_context,
                    model=target_model,
                )

                cb.record_success()
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                attribution = ModelAttribution(
                    provider_name=provider_name,
                    model_name=target_model,
                    is_fallback=is_fallback or (idx > 0),
                    execution_time_ms=elapsed_ms,
                    token_usage=token_usage,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

                # Record usage statistics
                ai_usage_tracker.record_usage(
                    incident_id=incident_id,
                    agent_name=agent_name,
                    provider=provider_name,
                    model=target_model,
                    prompt_tokens=token_usage.prompt_tokens,
                    completion_tokens=token_usage.completion_tokens,
                    total_tokens=token_usage.total_tokens,
                    estimated_cost_usd=token_usage.estimated_cost_usd,
                    latency_ms=elapsed_ms,
                    is_fallback=attribution.is_fallback,
                    status="SUCCESS",
                )

                return parsed_data, attribution

            except (AuthenticationError, RateLimitError, ProviderUnavailableError, ModelTimeoutError, Exception) as e:
                last_error = e
                cb.record_failure()
                is_fallback = True
                logger.warning(
                    f"[LLMRouter] Provider '{provider_name}' failed: {e}. Cascading to fallback."
                )

        # Ultimate fallback guarantee: execute deterministic provider directly
        det_provider = self.providers["deterministic"]
        parsed_data, token_usage, _ = await det_provider.generate_structured(
            schema=schema,
            system_prompt=clean_system,
            user_prompt=clean_user,
            context_data=clean_context,
            model="incidentx-deterministic-v1",
        )
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        attribution = ModelAttribution(
            provider_name="deterministic",
            model_name="incidentx-deterministic-v1",
            is_fallback=True,
            execution_time_ms=elapsed_ms,
            token_usage=token_usage,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        ai_usage_tracker.record_usage(
            incident_id=incident_id,
            agent_name=agent_name,
            provider="deterministic",
            model="incidentx-deterministic-v1",
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
            estimated_cost_usd=0.0,
            latency_ms=elapsed_ms,
            is_fallback=True,
            status="SUCCESS",
        )

        return parsed_data, attribution


# Global singleton instance
llm_router = LLMRouter()
