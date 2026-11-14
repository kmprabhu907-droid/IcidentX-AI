"""
INCIDENTX AI - Ollama Local Model LLM Provider (Phase 8.4)
Connects to local Ollama instances (e.g. Llama 3, Mistral, DeepSeek)
using JSON mode format with zero external cloud cost.
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
    BaseLLMProvider,
    ModelTimeoutError,
    ProviderUnavailableError,
)

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(BaseLLMProvider):
    """
    Ollama Local Model Provider.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(
            name="ollama",
            default_model=model or settings.OLLAMA_MODEL or "llama3:latest",
            timeout_seconds=timeout_seconds or settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.base_url = (base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")

    async def check_health(self) -> ProviderHealth:
        """Verify connectivity to local Ollama daemon."""
        if self._mock_sandbox_handler:
            mock_res = self._mock_sandbox_handler("health", {})
            return ProviderHealth(
                provider_name="ollama",
                status=mock_res.get("status", "AVAILABLE"),
                latency_ms=mock_res.get("latency_ms", 5.0),
                discovered_models=mock_res.get("models", ["llama3:latest"]),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout_seconds, 5.0)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                latency = round((time.perf_counter() - start_t) * 1000.0, 2)

                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return ProviderHealth(
                        provider_name="ollama",
                        status="AVAILABLE",
                        latency_ms=latency,
                        discovered_models=models,
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    return ProviderHealth(
                        provider_name="ollama",
                        status="ERROR",
                        latency_ms=latency,
                        error_message=f"Ollama returned HTTP {resp.status_code}",
                        checked_at=datetime.now(timezone.utc).isoformat(),
                    )
        except httpx.ConnectError:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="ollama",
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message=f"Local Ollama daemon is not running at {self.base_url}",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="ollama",
                status="UNAVAILABLE",
                latency_ms=latency,
                error_message=f"Connection to {self.base_url} timed out.",
                checked_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            latency = round((time.perf_counter() - start_t) * 1000.0, 2)
            return ProviderHealth(
                provider_name="ollama",
                status="ERROR",
                latency_ms=latency,
                error_message=str(e),
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

    async def list_models(self) -> List[str]:
        health = await self.check_health()
        return health.discovered_models or [self.default_model]

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
                prompt_tokens=mock_res.get("prompt_tokens", 90),
                completion_tokens=mock_res.get("completion_tokens", 45),
                total_tokens=mock_res.get("total_tokens", 135),
                estimated_cost_usd=0.0,
            )
            parsed = schema.model_validate_json(raw_text)
            return parsed, token_usage, raw_text

        messages = [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    f"Respond ONLY with valid JSON conforming to this schema:\n"
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
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code != 200:
                    raise ProviderUnavailableError(f"Ollama error {resp.status_code}: {resp.text}", provider="ollama")

                res_json = resp.json()
                raw_text = res_json.get("message", {}).get("content", "{}")

                p_tokens = res_json.get("prompt_eval_count", 0)
                c_tokens = res_json.get("eval_count", 0)
                t_tokens = p_tokens + c_tokens

                token_usage = TokenUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    estimated_cost_usd=0.0,  # Local inference is free
                )

                parsed = schema.model_validate_json(raw_text)
                return parsed, token_usage, raw_text

        except httpx.TimeoutException:
            raise ModelTimeoutError(f"Ollama request timed out after {self.timeout_seconds}s", provider="ollama")
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(f"Ollama connection refused at {self.base_url}: {str(e)}", provider="ollama")
        except ValidationError as e:
            raise ProviderUnavailableError(f"Ollama output failed schema validation: {str(e)}", provider="ollama")
