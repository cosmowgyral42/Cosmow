from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "COSMOW"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str

    openrouter_api_key: str = ""
    ai_model: str = "openrouter/free"

    daily_ai_request_limit: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()