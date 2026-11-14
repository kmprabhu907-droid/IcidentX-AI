"""
INCIDENTX AI - AI Providers Registry (Phase 8.4)
"""

from backend.app.services.ai.providers.base import (
    AuthenticationError,
    BaseLLMProvider,
    LLMProviderError,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from backend.app.services.ai.providers.deterministic_provider import DeterministicProvider
from backend.app.services.ai.providers.gemini_provider import GeminiProvider
from backend.app.services.ai.providers.ollama_provider import OllamaProvider
from backend.app.services.ai.providers.openai_provider import OpenAIProvider
from backend.app.services.ai.providers.vllm_provider import VLLMProvider

__all__ = [
    "BaseLLMProvider",
    "LLMProviderError",
    "AuthenticationError",
    "RateLimitError",
    "ProviderUnavailableError",
    "ModelTimeoutError",
    "GeminiProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "VLLMProvider",
    "DeterministicProvider",
]
