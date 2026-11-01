from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
FREE_AI_MODELS = frozenset({"openrouter/free"})


class Settings(BaseSettings):
    app_name: str = "COSMOW"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    ai_model: str = "openrouter/free"

    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = Field(default=768, ge=1, le=3072)
    gemini_embedding_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    rag_min_similarity: float = Field(default=0.70, ge=0.0, le=1.0)

    daily_ai_request_limit: int = Field(default=5, ge=0, le=100)
    global_daily_ai_call_limit: int = Field(default=50, ge=0, le=1000)

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)

    supabase_url: str = "https://cuozhqperbnvdwojurqp.supabase.co"
    supabase_jwks_timeout_seconds: float = Field(default=5.0, gt=0, le=30)

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("Invalid environment")

        if self.ai_model not in FREE_AI_MODELS:
            raise ValueError("AI model is not in the free-model allowlist")

        if self.environment == "production":
            if len(self.jwt_secret_key.encode("utf-8")) < 32:
                raise ValueError("Production JWT secret must be at least 32 bytes")

            if self.jwt_secret_key.strip().lower() in {
                "change-me",
                "your-secret-key",
                "test-only-secret",
            }:
                raise ValueError("Unsafe production JWT secret")

        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
