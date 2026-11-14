"""
INCIDENTX AI - Core Configuration Management
Implements environment-based configuration using Pydantic Settings.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "INCIDENTX AI"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = Field(default="development", description="Runtime environment: development, staging, production")
    APP_DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SECRET_KEY: str = Field(
        default="dev-insecure-secret-key-change-in-production-min32chars!",
        description="App secret key (minimum 32 characters required in production)"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info):
        # In production, require strong secrets (min 32 chars and not default dev key)
        env = info.data.get("APP_ENV", "development")
        if env == "production":
            if len(v) < 32 or "dev-insecure" in v:
                raise ValueError("In production, SECRET_KEY must be at least 32 characters and cannot use default dev secret.")
        return v

    # Networking & Security
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Enterprise Security & Auth Settings (Stage 6.1 & 6.2)
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_HSTS: bool = False
    ENABLE_RATE_LIMITING: bool = False
    RATE_LIMIT_DEFAULT_RPM: int = 5000
    RATE_LIMIT_MUTATION_RPM: int = 1000
    RATE_LIMIT_SIMULATION_RPM: int = 500
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024  # 2 Megabytes
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CSP_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' http: https: ws: wss:; "
        "frame-ancestors 'none';"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./incidentx.db",
        description="Async SQLAlchemy database connection string"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # Security & Guardrails
    ENABLE_EXECUTION_GUARDRAILS: bool = True
    REQUIRE_HUMAN_APPROVAL_MUTATION: bool = True

    # AI Provider & Investigation Intelligence (Phase 3 & Phase 8.4)
    AI_PROVIDER: str = Field(default="deterministic", description="AI Provider: deterministic, gemini, openai, anthropic, ollama, vllm")
    AI_PROVIDER_PRIMARY: str = Field(default="deterministic", description="Primary AI provider: deterministic, gemini, openai, ollama, vllm")
    AI_PROVIDER_SECONDARY: str = Field(default="deterministic", description="Secondary fallback AI provider")
    AI_MODEL: str = Field(default="incidentx-deterministic-v1", description="Default model identifier")
    AI_API_KEY: str = Field(default="", description="Generic API key for external LLM provider")
    AI_TEMPERATURE: float = Field(default=0.1, description="Sampling temperature")
    AI_REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0, description="Per-agent invocation timeout")
    AI_MAX_RETRIES: int = Field(default=2, description="Max retries on validation or rate limits")
    PROMPT_VERSION: str = Field(default="v3.0.0", description="Investigation prompt version tracking")

    # Specific Multi-Provider Credentials (Phase 8.4)
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro", description="Gemini model identifier")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o", description="OpenAI model identifier")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", description="OpenAI API base URL")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    OLLAMA_MODEL: str = Field(default="llama3:latest", description="Ollama model identifier")
    VLLM_BASE_URL: str = Field(default="http://localhost:8000/v1", description="vLLM API base URL")
    VLLM_MODEL: str = Field(default="default", description="vLLM model identifier")

    # Budget & Circuit Breaker Guardrails (Phase 8.4)
    AI_DAILY_TOKEN_BUDGET: int = Field(default=500000, description="Max daily token budget")
    AI_CIRCUIT_BREAKER_MAX_FAILURES: int = Field(default=3, description="Consecutive failures before circuit breaker trips")
    AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = Field(default=60.0, description="Circuit breaker cooldown in seconds")

    # Phase 8.3 Live Observability Integrations (Prometheus, OpenTelemetry, Grafana)
    PROMETHEUS_URL: str = Field(default="http://localhost:9090", description="Prometheus API base URL")
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus integration")
    PROMETHEUS_TIMEOUT_SECONDS: float = Field(default=5.0, description="Timeout for Prometheus queries")
    PROMETHEUS_BEARER_TOKEN: str = Field(default="", description="Bearer token for Prometheus authentication")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4318", description="OTel collector HTTP endpoint")
    OTEL_ENABLED: bool = Field(default=True, description="Enable OpenTelemetry trace collection")
    OTEL_MAX_BUFFERED_TRACES: int = Field(default=500, description="Max traces stored in in-memory buffer")
    GRAFANA_URL: str = Field(default="http://localhost:3001", description="Grafana base URL")
    GRAFANA_API_KEY: str = Field(default="", description="Grafana API key or Service Account token")
    GRAFANA_ENABLED: bool = Field(default=True, description="Enable Grafana integration")
    GRAFANA_DEFAULT_DASHBOARD_UID: str = Field(default="incidentx-cluster", description="Default Grafana dashboard UID")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
