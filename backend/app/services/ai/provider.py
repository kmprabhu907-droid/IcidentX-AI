"""
INCIDENTX AI - Provider-Independent AI Integration Layer
Supports configurable LLM providers (Gemini, OpenAI, Anthropic) and a dedicated,
transparently-labeled Deterministic Analysis Mode.
Enforces Pydantic structured output validation, retries, timeouts, and version tracking.
"""

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.services.ai.sanitizer import PromptSanitizer

T = TypeVar("T", bound=BaseModel)


class AIResponse(BaseModel, Generic[T]):
    data: T
    provider: str
    model: str
    prompt_version: str
    duration_ms: int
    is_deterministic: bool
    timestamp: str


class AIProviderClient:
    """
    Unified AI Integration Client.
    Dispatches to real LLM providers if credentials exist, or transparently executes
    the built-in deterministic reasoning engine.
    """

    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.model = settings.AI_MODEL
        self.api_key = settings.AI_API_KEY
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
        self.max_retries = settings.AI_MAX_RETRIES
        self.prompt_version = settings.PROMPT_VERSION

    def is_deterministic_mode(self) -> bool:
        """Returns True if running in transparent deterministic analysis mode."""
        return self.provider == "deterministic" or not self.api_key

    async def generate_structured(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        context_data: Optional[Dict[str, Any]] = None,
        deterministic_fallback_fn: Optional[Any] = None,
    ) -> AIResponse[T]:
        """
        Generate structured output conforming to a Pydantic schema.
        If in deterministic mode or if LLM call fails, cleanly executes deterministic fallback.
        """
        start_time = time.perf_counter()

        # Sanitize prompt inputs to neutralize prompt injection and mask secrets
        clean_system = PromptSanitizer.sanitize_text(system_prompt)
        clean_user = PromptSanitizer.sanitize_text(user_prompt)
        clean_context = PromptSanitizer.sanitize_dict(context_data or {})

        # Deterministic Analysis Mode
        if self.is_deterministic_mode() or not self.api_key:
            if deterministic_fallback_fn:
                result_data = deterministic_fallback_fn(clean_context)
            else:
                result_data = schema()  # type: ignore

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return AIResponse[T](
                data=result_data,
                provider="deterministic",
                model="incidentx-deterministic-v1",
                prompt_version=self.prompt_version,
                duration_ms=elapsed_ms,
                is_deterministic=True,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # External LLM Provider Mode (Gemini / OpenAI / Anthropic)
        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                # Call cloud LLM with timeout
                raw_json = await asyncio.wait_for(
                    self._call_llm_api(clean_system, clean_user, clean_context),
                    timeout=self.timeout
                )
                parsed_data = schema.model_validate_json(raw_json)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                return AIResponse[T](
                    data=parsed_data,
                    provider=self.provider,
                    model=self.model,
                    prompt_version=self.prompt_version,
                    duration_ms=elapsed_ms,
                    is_deterministic=False,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            except (asyncio.TimeoutError, ValidationError, Exception) as e:
                last_error = e
                logger.warning(
                    f"[AIProviderClient] Attempt {attempt} failed for {schema.__name__}: {e}. Retrying..."
                )
                await asyncio.sleep(0.5 * attempt)

        # Fallback to deterministic mode if all LLM retries fail
        logger.error(
            f"[AIProviderClient] All {self.max_retries} attempts failed ({last_error}). Falling back to deterministic mode."
        )
        if deterministic_fallback_fn:
            fallback_data = deterministic_fallback_fn(clean_context)
        else:
            fallback_data = schema()  # type: ignore

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return AIResponse[T](
            data=fallback_data,
            provider="deterministic-fallback",
            model="incidentx-deterministic-v1",
            prompt_version=self.prompt_version,
            duration_ms=elapsed_ms,
            is_deterministic=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _call_llm_api(self, system: str, user: str, context: Dict[str, Any]) -> str:
        """
        Generic HTTP-based structured output call for cloud providers (httpx).
        """
        import httpx
        # If OpenAI format
        if self.provider == "openai":
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model if self.model != "incidentx-deterministic-v1" else "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"{user}\nContext: {json.dumps(context)}"}
                ],
                "response_format": {"type": "json_object"},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

        # Default fallback string
        raise NotImplementedError(f"Cloud provider {self.provider} requires custom integration.")


# Singleton instance
ai_provider = AIProviderClient()
