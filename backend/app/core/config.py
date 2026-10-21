from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "COSMOW"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 30.0
    ai_model: str = "openrouter/free"

    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 768
    gemini_embedding_timeout_seconds: float = 15.0

    daily_ai_request_limit: int = 5
    global_daily_ai_call_limit: int = 50

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    supabase_url: str = "https://cuozhqperbnvdwojurqp.supabase.co"
    supabase_jwks_timeout_seconds: float = 5.0

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
