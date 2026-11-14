"""
INCIDENTX AI - Google Gemini LLM Provider (Phase 8.4)
Connects to Google Gemini API (v1beta) using structured JSON generation,
token tracking via usageMetadata, and robust error classification.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from backend.app.core.config import settings
from backend.app.services.ai.models import ProviderHealth, TokenUsage
from backend.app.services.ai.providers.base import (
    AuthenticationError,
    BaseLLMProvider,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API Provider.
    """

    PRICING = {
        "gemini-1.5-pro": {"input_per_million": 1.25, "output_per_million": 5.00},
        "gemini-1.5-flash": {"input_per_million": 0.075, "output_per_million": 0.30},
        "gemini-2.0-flash-exp": {"input_per_million": 0.0, "output_per_million": 0.0},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(
            name="gemini",
            default_model=model or settings.GEMINI_MODEL or "gemini-1.5-pro",
            timeout_seconds=timeout_seconds or settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(model, self.PRICING["gemini-1.5-pro"])
        cost = (prompt_tokens / 1_000_000.0 * pricing["input_per_million"]) + (
            completion_tokens / 1_000_000.0 * pricing["output_per_million"]
        )
        return round(cost, 6)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def check_health(self) -> ProviderHealth:
        """Verify connectivity to Gemini API."""
        if not self.api_key:
            return ProviderHealth(
                provider_name="gemini",
                status="NOT_CONFIGURED",
                latency_ms=0.0,
                error_message="GEMINI_API_KEY is not configured.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        if self._mock_sandbox_handler:
            mock_res = self._mock_sandbox_handler("health", {})
            return ProviderHealth(
                provider_name="gemini",
                status=mock_res.get("status", "AVAILABLE"),
                latency_ms=mock_res.get("latency_ms", 15.0),
                discovered_models=mock_res.get("models", ["gemini-1.5-pro", "gemini-1.5-flash"]),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                url = f"{self.base_url}/models?key={self.api_key}"
                resp = await client.get(url)
                latency = round((time.perf_counter() - start_t) * 1000.0, 2)

                if resp.status_code == 200:
                    data = resp.json()
                    models = [
                        m["name"].replace("models/", "")
                        for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    return ProviderHealth(
                        provider_name="gemini",
                        status="AVAILABLE",
                        latency_ms=latency,
                        discovered_models=models[:10],
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code in (401, 403):
                    return ProviderHealth(
                        provider_name="gemini",
                        status="ERROR",
                        latency_ms=latency,
                        error_message="Authentication failed: Invalid or unauthorized GEMINI_API_KEY.",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code == 429:
                    return ProviderHealth(
                        provider_name="gemini",
                        status="DEGRADED",
                        latency_ms=latency,
                        error_message="Rate limit or quota exceeded on Gemini API.",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderHealth(
                        provider_name="gemini",
                        status="ERROR",
                        latency_ms=latency,
                        error_message=f"Gemini API returned HTTP {resp.status_code}",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
        except httpx.ConnectError as e:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="gemini",
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message=f"Network connection failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="gemini",
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message="Request to Gemini API timed out.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="gemini",
                status="ERROR",
                latency_ms=latency,
                error_message=str(e),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

    async def list_models(self) -> List[str]:
        health = await self.check_health()
        return health.discovered_models or ["gemini-1.5-pro", "gemini-1.5-flash"]

    async def generate_structured(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        context_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Tuple[T, TokenUsage, str]:
        selected_model = model or self.default_model

        if self._mock_sandbox_handler:
            mock_res = self._mock_sandbox_handler(
                "generate_structured",
                {
                    "schema": schema,
                    "system": system_prompt,
                    "user": user_prompt,
                    "context": context_data,
                    "model": selected_model,
                },
            )
            raw_text = mock_res.get("raw_text", "{}")
            token_usage = TokenUsage(
                prompt_tokens=mock_res.get("prompt_tokens", 100),
                completion_tokens=mock_res.get("completion_tokens", 50),
                total_tokens=mock_res.get("total_tokens", 150),
                estimated_cost_usd=self._estimate_cost(selected_model, 100, 50),
            )
            parsed = schema.model_validate_json(raw_text)
            return parsed, token_usage, raw_text

        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY is not configured.", provider="gemini")

        # Construct Gemini API payload
        json_schema_prompt = (
            f"\n\nYou MUST respond with valid JSON adhering strictly to this JSON schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}"
        )
        full_system = f"{system_prompt}{json_schema_prompt}"

        contents = []
        if context_data:
            contents.append({"role": "user", "parts": [{"text": f"Context Evidence Data:\n{json.dumps(context_data, indent=2)}"}]})
        contents.append({"role": "user", "parts": [{"text": user_prompt}]})

        payload = {
            "system_instruction": {"parts": [{"text": full_system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        url = f"{self.base_url}/models/{selected_model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, json=payload)

                if resp.status_code in (401, 403):
                    raise AuthenticationError(f"Gemini API authentication failed: {resp.text}", provider="gemini")
                elif resp.status_code == 429:
                    raise RateLimitError(f"Gemini rate limit exceeded: {resp.text}", provider="gemini")
                elif resp.status_code != 200:
                    raise ProviderUnavailableError(f"Gemini API error {resp.status_code}: {resp.text}", provider="gemini")

                res_json = resp.json()
                candidates = res_json.get("candidates", [])
                if not candidates:
                    raise ProviderUnavailableError("Gemini returned empty candidate response.", provider="gemini")

                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")

                # Parse token usage
                usage_meta = res_json.get("usageMetadata", {})
                p_tokens = usage_meta.get("promptTokenCount", 0)
                c_tokens = usage_meta.get("candidatesTokenCount", 0)
                t_tokens = usage_meta.get("totalTokenCount", p_tokens + c_tokens)
                cost = self._estimate_cost(selected_model, p_tokens, c_tokens)

                token_usage = TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=cost,
                )

                parsed = schema.model_validate_json(raw_text)
                return parsed, token_usage, raw_text

        except httpx.TimeoutException:
            raise ModelTimeoutError(f"Gemini request timed out after {self.timeout_seconds}s", provider="gemini")
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(f"Gemini connection failed: {str(e)}", provider="gemini")
        except ValidationError as e:
            raise ProviderUnavailableError(f"Gemini output failed schema validation: {str(e)}", provider="gemini")
