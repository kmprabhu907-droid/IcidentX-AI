"""
INCIDENTX AI - Base LLM Provider Interface (Phase 8.4)
Defines abstract contracts, health monitoring, structured generation protocols,
and error classifications for multi-provider AI reasoning.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel

from backend.app.services.ai.models import ProviderHealth, TokenUsage

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(Exception):
    """Base error for LLM provider operations."""
    def __init__(self, message: str, provider: str, error_type: str = "GENERIC_ERROR"):
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type


class AuthenticationError(LLMProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, error_type="AUTHENTICATION_FAILURE")


class RateLimitError(LLMProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, error_type="RATE_LIMITED")


class ProviderUnavailableError(LLMProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, error_type="UNAVAILABLE")


class ModelTimeoutError(LLMProviderError):
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, error_type="TIMEOUT")


class BaseLLMProvider(ABC):
    """
    Abstract contract for an AI provider (Gemini, OpenAI, Ollama, vLLM, Deterministic).
    """

    def __init__(self, name: str, default_model: str, timeout_seconds: float = 30.0):
        self.name = name
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._mock_sandbox_handler: Optional[Callable[[str, Dict[str, Any]], Any]] = None

    def set_mock_sandbox_handler(self, handler: Optional[Callable[[str, Dict[str, Any]], Any]]) -> None:
        """Inject a deterministic sandbox handler for integration testing without external APIs."""
        self._mock_sandbox_handler = handler

    @property
    def is_configured(self) -> bool:
        """Indicates whether this provider has sufficient credentials/configuration to be invoked."""
        return True

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Probe connectivity, authenticate, and measure latency."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Discover available model identifiers supported by the provider."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        context_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Tuple[T, TokenUsage, str]:
        """
        Generate structured output adhering to a Pydantic schema.
        Returns: (parsed_pydantic_instance, token_usage, raw_text_response)
        """
        pass
