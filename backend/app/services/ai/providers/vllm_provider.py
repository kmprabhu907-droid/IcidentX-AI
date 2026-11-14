"""
INCIDENTX AI - vLLM Provider (Phase 8.4)
Connects to self-hosted vLLM inference servers using OpenAI-compatible APIs.
"""

from typing import Optional
from backend.app.core.config import settings
from backend.app.services.ai.providers.openai_provider import OpenAIProvider


class VLLMProvider(OpenAIProvider):
    """
    vLLM Provider utilizing OpenAI-compatible endpoints with local cost accounting ($0.00).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        super().__init__(
            api_key="vllm-local-token",
            model=model or settings.VLLM_MODEL or "default",
            base_url=base_url or settings.VLLM_BASE_URL or "http://localhost:8000/v1",
            timeout_seconds=timeout_seconds or settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
        self.name = "vllm"

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Self-hosted inference has $0.00 API token cost
        return 0.0
