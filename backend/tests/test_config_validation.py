import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("openrouter_timeout_seconds", 0),
        ("openrouter_timeout_seconds", 121),
        ("gemini_embedding_timeout_seconds", 0),
        ("gemini_embedding_timeout_seconds", 121),
        ("gemini_embedding_dimensions", 0),
        ("gemini_embedding_dimensions", 3073),
        ("daily_ai_request_limit", -1),
        ("daily_ai_request_limit", 101),
        ("global_daily_ai_call_limit", -1),
        ("global_daily_ai_call_limit", 1001),
        ("access_token_expire_minutes", 0),
        ("access_token_expire_minutes", 1441),
        ("supabase_jwks_timeout_seconds", 0),
        ("supabase_jwks_timeout_seconds", 31),
    ],
)
def test_invalid_security_configuration_is_rejected(field, value):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/cosmow_test",
            jwt_secret_key="test-only-secret",
            **{field: value},
        )


def test_zero_ai_quotas_are_allowed_to_disable_usage():
    settings = Settings(
        database_url="postgresql://localhost/cosmow_test",
        jwt_secret_key="test-only-secret",
        daily_ai_request_limit=0,
        global_daily_ai_call_limit=0,
    )

    assert settings.daily_ai_request_limit == 0
    assert settings.global_daily_ai_call_limit == 0

@pytest.mark.parametrize(
    "secret",
    ["test-only-secret", "short"],
)
def test_production_rejects_weak_jwt_secrets(secret):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/cosmow_test",
            jwt_secret_key=secret,
            environment="production",
        )


def test_production_accepts_strong_jwt_secret():
    settings = Settings(
        database_url="postgresql://localhost/cosmow_test",
        jwt_secret_key="a" * 64,
        environment="production",
    )
    assert settings.environment == "production"


def test_invalid_environment_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/cosmow_test",
            jwt_secret_key="test-only-secret",
            environment="prod",
        )

def test_paid_ai_model_is_rejected():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://localhost/cosmow_test",
            jwt_secret_key="test-only-secret",
            ai_model="openai/gpt-4o",
        )


def test_free_ai_model_is_accepted():
    settings = Settings(
        database_url="postgresql://localhost/cosmow_test",
        jwt_secret_key="test-only-secret",
        ai_model="openrouter/free",
    )
    assert settings.ai_model == "openrouter/free"
