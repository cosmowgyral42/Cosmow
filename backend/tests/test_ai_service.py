
from unittest.mock import Mock, patch

import pytest

from app.ai.schemas import AIRequest, AIResponse
from app.services.ai_service import (
    AIService,
    AIServiceError,
    AIServiceQuotaError,
)
from app.models.user import User


def make_user():
    return User(
        id=1,
        email="service@example.com",
        password_hash="hashed",
        is_active=True,
        timezone="UTC",
    )


def test_ai_service_success():
    provider = Mock()
    provider.generate.return_value = AIResponse(
        content="Successful response",
        model="test-model",
        provider="mock",
    )

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ) as reserve, patch(
        "app.services.ai_service.finalize_ai_call"
    ) as finalize, patch(
        "app.services.ai_service.release_ai_call"
    ) as release:

        result = service.generate(
            db=db,
            user=user,
            request=AIRequest(prompt="Hello"),
        )

    assert result.content == "Successful response"
    reserve.assert_called_once_with(db, user)
    provider.generate.assert_called_once()
    finalize.assert_called_once_with(db, user, reserve.return_value)
    release.assert_not_called()


def test_ai_service_releases_quota_on_provider_failure():
    provider = Mock()
    provider.generate.side_effect = RuntimeError("provider failed")

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ) as reserve, patch(
        "app.services.ai_service.finalize_ai_call"
    ) as finalize, patch(
        "app.services.ai_service.release_ai_call"
    ) as release:

        with pytest.raises(
            AIServiceError,
            match="temporarily unavailable",
        ):
            service.generate(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            )

    reserve.assert_called_once_with(db, user)
    provider.generate.assert_called_once()
    release.assert_called_once_with(db, user, reserve.return_value)
    finalize.assert_not_called()


def test_ai_service_does_not_call_provider_when_quota_rejected():
    provider = Mock()

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call",
        side_effect=ValueError("Daily AI request limit reached."),
    ) as reserve:

        with pytest.raises(
            AIServiceQuotaError,
            match="Daily AI request limit reached",
        ):
            service.generate(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            )

    reserve.assert_called_once_with(db, user)
    provider.generate.assert_not_called()


def test_ai_service_retries_transient_finalize_failure():
    provider = Mock()
    provider.generate.return_value = AIResponse(
        content="Successful response",
        model="test-model",
        provider="mock",
    )

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ) as reserve, patch(
        "app.services.ai_service.finalize_ai_call",
        side_effect=[RuntimeError("temporary database failure"), None],
    ) as finalize, patch(
        "app.services.ai_service.release_ai_call"
    ) as release:
        result = service.generate(
            db=db,
            user=user,
            request=AIRequest(prompt="Hello"),
        )

    assert result.content == "Successful response"
    reserve.assert_called_once_with(db, user)
    provider.generate.assert_called_once()
    assert finalize.call_count == 2
    finalize.assert_called_with(db, user, reserve.return_value)
    db.rollback.assert_called_once()
    release.assert_not_called()


def test_ai_service_handles_persistent_finalize_failure():
    provider = Mock()
    provider.generate.return_value = AIResponse(
        content="Successful response",
        model="test-model",
        provider="mock",
    )

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ) as reserve, patch(
        "app.services.ai_service.finalize_ai_call",
        side_effect=RuntimeError("finalization failed"),
    ) as finalize, patch(
        "app.services.ai_service.release_ai_call"
    ) as release:
        with pytest.raises(
            AIServiceError,
            match="AI usage could not be finalized",
        ):
            service.generate(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            )

    reserve.assert_called_once_with(db, user)
    provider.generate.assert_called_once()
    assert finalize.call_count == 2
    finalize.assert_called_with(db, user, reserve.return_value)
    assert db.rollback.call_count == 2
    release.assert_not_called()



def test_provider_rate_limit_releases_reserved_quota(monkeypatch):
    from types import SimpleNamespace

    from app.ai.providers.openrouter import AIProviderRateLimitError
    from app.services import ai_service as service_module
    from app.services.ai_service import AIServiceRateLimitError

    db = SimpleNamespace(rollback=Mock())
    user = SimpleNamespace(id=42)
    provider = SimpleNamespace(
        generate=Mock(
            side_effect=AIProviderRateLimitError(
                "OpenRouter request failed with status 429 (rate limit)."
            )
        )
    )
    reserve = Mock()
    release = Mock()
    finalize = Mock()

    monkeypatch.setattr(service_module, "reserve_ai_call", reserve)
    monkeypatch.setattr(service_module, "release_ai_call", release)
    monkeypatch.setattr(service_module, "finalize_ai_call", finalize)

    service = AIService(provider=provider)

    with pytest.raises(AIServiceRateLimitError):
        service.generate(
            db=db,
            user=user,
            request=AIRequest(prompt="test"),
        )

    reserve.assert_called_once_with(db, user)
    release.assert_called_once_with(db, user, reserve.return_value)
    finalize.assert_not_called()
    provider.generate.assert_called_once()


def test_stream_finalizes_quota_after_success():
    from types import SimpleNamespace

    from app.services import ai_service as service_module

    db = SimpleNamespace(rollback=Mock())
    user = SimpleNamespace(id=42)
    provider = Mock()
    provider.stream.return_value = iter(["one", "two"])
    service = AIService(provider)

    with patch.object(service_module, "reserve_ai_call") as reserve:
        with patch.object(service_module, "finalize_ai_call") as finalize:
            with patch.object(service_module, "release_ai_call") as release:
                result = list(
                    service.stream(
                        db,
                        user,
                        AIRequest(prompt="test"),
                    )
                )

    assert result == ["one", "two"]
    reserve.assert_called_once_with(db, user)
    finalize.assert_called_once_with(db, user, reserve.return_value)
    release.assert_not_called()


def test_stream_finalizes_quota_when_consumer_closes_after_content():
    from types import SimpleNamespace

    from app.services import ai_service as service_module

    db = SimpleNamespace(rollback=Mock())
    user = SimpleNamespace(id=42)
    provider = Mock()
    provider.stream.return_value = iter(["first", "second"])
    service = AIService(provider)

    with patch.object(service_module, "reserve_ai_call") as reserve:
        with patch.object(service_module, "finalize_ai_call") as finalize:
            with patch.object(service_module, "release_ai_call") as release:
                stream = service.stream(
                    db,
                    user,
                    AIRequest(prompt="test"),
                )
                assert next(stream) == "first"
                stream.close()

    reserve.assert_called_once_with(db, user)
    release.assert_not_called()
    finalize.assert_called_once_with(db, user, reserve.return_value)


@pytest.mark.parametrize("failure_kind", ["provider_error", "provider_rate_limit"])
def test_failed_provider_calls_do_not_consume_quota(unique_email, failure_kind):
    from app.ai.providers.openrouter import AIProviderRateLimitError
    from app.core.database import SessionLocal
    from app.models.ai_global_usage import AIGlobalUsage
    from app.models.ai_quota_reservation import AIQuotaReservation
    from app.models.ai_usage import AIUsage
    from app.services.ai_quota import get_global_today, get_user_today
    from app.services.ai_service import AIServiceRateLimitError

    db = SessionLocal()

    try:
        user = User(
            email=unique_email,
            password_hash="test_hash",
            timezone="UTC",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_today = get_user_today(user)
        global_today = get_global_today()

        global_before = db.query(AIGlobalUsage).filter(
            AIGlobalUsage.usage_date == global_today
        ).first()

        global_success_before = (
            global_before.successful_call_count if global_before else 0
        )
        global_reserved_before = (
            global_before.reserved_count if global_before else 0
        )

        provider = Mock()

        if failure_kind == "provider_rate_limit":
            provider.generate.side_effect = AIProviderRateLimitError(
                "Provider rate limit reached."
            )
        else:
            provider.generate.side_effect = RuntimeError("Provider failed.")

        service = AIService(provider)

        with pytest.raises(AIServiceError):
            service.generate(
                db=db,
                user=user,
                request=AIRequest(prompt="Test failed provider call"),
            )

        db.expire_all()

        user_usage = db.query(AIUsage).filter(
            AIUsage.user_id == user.id,
            AIUsage.usage_date == user_today,
        ).one()

        global_usage = db.query(AIGlobalUsage).filter(
            AIGlobalUsage.usage_date == global_today
        ).one()

        reservation = db.query(AIQuotaReservation).filter(
            AIQuotaReservation.user_id == user.id
        ).one()

        assert reservation.status == "released"
        assert reservation.completed_at is not None

        assert user_usage.request_count == 0
        assert user_usage.reserved_count == 0

        assert global_usage.successful_call_count == global_success_before
        assert global_usage.reserved_count == global_reserved_before

        provider.generate.assert_called_once()

    finally:
        db.close()
