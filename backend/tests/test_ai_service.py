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
    finalize.assert_called_once_with(db, user)
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
    release.assert_called_once_with(db, user)
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
    finalize.assert_called_once_with(db, user)
    db.rollback.assert_called_once()
