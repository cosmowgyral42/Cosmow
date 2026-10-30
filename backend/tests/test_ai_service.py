from unittest.mock import Mock, patch

import pytest

from app.ai.schemas import AIRequest, AIResponse
from app.services.ai_service import AIService, AIServiceError
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
            AIServiceError,
            match="Daily AI request limit reached",
        ):
            service.generate(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            )

    reserve.assert_called_once_with(db, user)
    provider.generate.assert_not_called()


def test_ai_service_handles_finalize_failure():
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
    ) as finalize:

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
    finalize.assert_called_once_with(db, user, reserve.return_value)
    db.rollback.assert_called_once()


def test_provider_rate_limit_releases_reserved_quota(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from app.ai.providers.openrouter import AIProviderRateLimitError
    from app.ai.schemas import AIRequest
    from app.services import ai_service as service_module
    from app.services.ai_service import (
        AIService,
        AIServiceRateLimitError,
    )

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

    try:
        service.generate(db=db, user=user, request=AIRequest(prompt="test"))
    except AIServiceRateLimitError:
        pass
    else:
        raise AssertionError("Expected AIServiceRateLimitError")

    reserve.assert_called_once_with(db, user)
    release.assert_called_once_with(db, user, reserve.return_value)
    finalize.assert_not_called()
    provider.generate.assert_called_once()



def test_stream_finalizes_quota_after_success():
    from types import SimpleNamespace

    from app.ai.schemas import AIRequest
    from app.services import ai_service as service_module

    db = SimpleNamespace(rollback=Mock())
    user = SimpleNamespace(id=42)
    provider = Mock()
    provider.stream.return_value = iter(["one", "two"])
    service = AIService(provider)

    with patch.object(service_module, "reserve_ai_call") as reserve:
        with patch.object(service_module, "finalize_ai_call") as finalize:
            with patch.object(service_module, "release_ai_call") as release:
                result = list(service.stream(db, user, AIRequest(prompt="test")))

    assert result == ["one", "two"]
    reserve.assert_called_once_with(db, user)
    finalize.assert_called_once_with(db, user, reserve.return_value)
    release.assert_not_called()


def test_stream_releases_quota_when_consumer_closes_early():
    from types import SimpleNamespace

    from app.ai.schemas import AIRequest
    from app.services import ai_service as service_module

    db = SimpleNamespace(rollback=Mock())
    user = SimpleNamespace(id=42)
    provider = Mock()
    provider.stream.return_value = iter(["first", "second"])
    service = AIService(provider)

    with patch.object(service_module, "reserve_ai_call") as reserve:
        with patch.object(service_module, "finalize_ai_call") as finalize:
            with patch.object(service_module, "release_ai_call") as release:
                stream = service.stream(db, user, AIRequest(prompt="test"))
                assert next(stream) == "first"
                stream.close()

    reserve.assert_called_once_with(db, user)
    release.assert_called_once_with(db, user, reserve.return_value)
    finalize.assert_not_called()
