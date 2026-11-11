"""
INCIDENTX AI - Core Configuration Management
Implements environment-based configuration using Pydantic Settings.
"""

from typing import List
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
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Enterprise Security Settings (Stage 6.1)
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_HSTS: bool = False
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_DEFAULT_RPM: int = 120
    RATE_LIMIT_MUTATION_RPM: int = 30
    RATE_LIMIT_SIMULATION_RPM: int = 15
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024  # 2 Megabytes
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

    # AI Provider & Investigation Intelligence (Phase 3)
    AI_PROVIDER: str = Field(default="deterministic", description="AI Provider: deterministic, gemini, openai, anthropic")
    AI_MODEL: str = Field(default="incidentx-deterministic-v1", description="Model identifier")
    AI_API_KEY: str = Field(default="", description="API key for external LLM provider")
    AI_TEMPERATURE: float = Field(default=0.1, description="Sampling temperature")
    AI_REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0, description="Per-agent invocation timeout")
    AI_MAX_RETRIES: int = Field(default=2, description="Max retries on validation or rate limits")
    PROMPT_VERSION: str = Field(default="v3.0.0", description="Investigation prompt version tracking")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
