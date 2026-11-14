"""
INCIDENTX AI - OpenAI LLM Provider (Phase 8.4)
Connects to OpenAI API using JSON schema mode, token usage tracking, and error mapping.
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


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API Provider.
    """

    PRICING = {
        "gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00},
        "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
        "gpt-4-turbo": {"input_per_million": 10.00, "output_per_million": 30.00},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(
            name="openai",
            default_model=model or settings.OPENAI_MODEL or "gpt-4o",
            timeout_seconds=timeout_seconds or settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
        cost = (prompt_tokens / 1_000_000.0 * pricing["input_per_million"]) + (
            completion_tokens / 1_000_000.0 * pricing["output_per_million"]
        )
        return round(cost, 6)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers["HTTP-Referer"] = "http://localhost:3000"
        headers["X-Title"] = "TitanIQ IncidentX"
        return headers

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def check_health(self) -> ProviderHealth:
        """Verify connectivity to OpenAI API."""
        if not self.api_key:
            return ProviderHealth(
                provider_name=self.name,
                status="NOT_CONFIGURED",
                latency_ms=0.0,
                error_message=f"{self.name.upper()}_API_KEY is not configured.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        if self._mock_sandbox_handler:
            mock_res = self._mock_sandbox_handler("health", {})
            return ProviderHealth(
                provider_name=self.name,
                status=mock_res.get("status", "AVAILABLE"),
                latency_ms=mock_res.get("latency_ms", 12.0),
                discovered_models=mock_res.get("models", ["gpt-4o", "gpt-4o-mini"]),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._get_headers())
                latency = round((time.perf_counter() - start_t) * 1000.0, 2)

                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return ProviderHealth(
                        provider_name=self.name,
                        status="AVAILABLE",
                        latency_ms=latency,
                        discovered_models=models[:10],
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code == 401:
                    return ProviderHealth(
                        provider_name=self.name,
                        status="ERROR",
                        latency_ms=latency,
                        error_message=f"Authentication failed: Invalid {self.name.upper()}_API_KEY.",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                elif resp.status_code == 429:
                    return ProviderHealth(
                        provider_name=self.name,
                        status="DEGRADED",
                        latency_ms=latency,
                        error_message=f"Rate limit or quota exhausted on {self.name} API.",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderHealth(
                        provider_name=self.name,
                        status="ERROR",
                        latency_ms=latency,
                        error_message=f"{self.name} API returned HTTP {resp.status_code}",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
        except httpx.ConnectError as e:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name=self.name,
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message=f"Network connection failed: {str(e)}",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name=self.name,
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message=f"Request to {self.name} API timed out.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name=self.name,
                status="ERROR",
                latency_ms=latency,
                error_message=str(e),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

    async def list_models(self) -> List[str]:
        health = await self.check_health()
        return health.discovered_models or ["gpt-4o", "gpt-4o-mini"]

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
                prompt_tokens=mock_res.get("prompt_tokens", 120),
                completion_tokens=mock_res.get("completion_tokens", 60),
                total_tokens=mock_res.get("total_tokens", 180),
                estimated_cost_usd=self._estimate_cost(selected_model, 120, 60),
            )
            parsed = schema.model_validate_json(raw_text)
            return parsed, token_usage, raw_text

        if not self.api_key:
            raise AuthenticationError("OPENAI_API_KEY is not configured.", provider="openai")

        messages = [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    f"You MUST respond ONLY with valid JSON matching this schema:\n"
                    f"{json.dumps(schema.model_json_schema(), indent=2)}"
                ),
            }
        ]
        if context_data:
            messages.append({"role": "user", "content": f"Context Evidence Data:\n{json.dumps(context_data, indent=2)}"})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": selected_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=self._get_headers(), json=payload)

                if resp.status_code == 401:
                    raise AuthenticationError(f"OpenAI API authentication failed: {resp.text}", provider="openai")
                elif resp.status_code == 429:
                    raise RateLimitError(f"OpenAI rate limit exceeded: {resp.text}", provider="openai")
                elif resp.status_code != 200:
                    raise ProviderUnavailableError(f"OpenAI API error {resp.status_code}: {resp.text}", provider="openai")

                res_json = resp.json()
                raw_text = res_json["choices"][0]["message"]["content"]
                usage = res_json.get("usage", {})

                p_tokens = usage.get("prompt_tokens", 0)
                c_tokens = usage.get("completion_tokens", 0)
                t_tokens = usage.get("total_tokens", p_tokens + c_tokens)
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
            raise ModelTimeoutError(f"OpenAI request timed out after {self.timeout_seconds}s", provider="openai")
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(f"OpenAI connection failed: {str(e)}", provider="openai")
        except ValidationError as e:
            raise ProviderUnavailableError(f"OpenAI output failed schema validation: {str(e)}", provider="openai")
