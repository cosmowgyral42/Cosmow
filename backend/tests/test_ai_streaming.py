from unittest.mock import Mock, patch

import pytest

from app.ai.schemas import AIRequest
from app.services.ai_service import AIService, AIServiceError
from app.models.user import User


def make_user():
    return User(
        id=1,
        email="stream@example.com",
        password_hash="hashed",
        is_active=True,
        timezone="UTC",
    )


def test_stream_success_finalizes_quota():
    provider = Mock()
    provider.stream.return_value = iter(["Hello ", "COSMOW"])

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

        result = list(
            service.stream(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            )
        )

    assert result == ["Hello ", "COSMOW"]
    reserve.assert_called_once_with(db, user)
    finalize.assert_called_once_with(db, user)
    release.assert_not_called()


def test_stream_failure_releases_quota():
    provider = Mock()

    def failing_stream(request):
        yield "Partial "
        raise RuntimeError("stream failed")

    provider.stream.side_effect = failing_stream

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
            list(
                service.stream(
                    db=db,
                    user=user,
                    request=AIRequest(prompt="Hello"),
                )
            )

    reserve.assert_called_once_with(db, user)
    release.assert_called_once_with(db, user)
    finalize.assert_not_called()


def test_stream_quota_rejection_does_not_call_provider():
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
            list(
                service.stream(
                    db=db,
                    user=user,
                    request=AIRequest(prompt="Hello"),
                )
            )

    reserve.assert_called_once_with(db, user)
    provider.stream.assert_not_called()
