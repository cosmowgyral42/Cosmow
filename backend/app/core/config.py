from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "COSMOW"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    openrouter_api_key: str = ""
    ai_model: str = "openrouter/free"

    daily_ai_request_limit: int = 5
    global_daily_ai_call_limit: int = 50

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
