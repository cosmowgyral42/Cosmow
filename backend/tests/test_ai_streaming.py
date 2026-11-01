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
    finalize.assert_called_once_with(db, user, reserve.return_value)
    release.assert_not_called()


def test_stream_partial_failure_consumes_quota():
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
    release.assert_not_called()
    finalize.assert_called_once_with(db, user, reserve.return_value)


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

def test_stream_logs_quota_cleanup_failure(caplog):
    provider = Mock()
    provider.stream.return_value = iter(["partial"])

    service = AIService(provider)
    db = Mock()
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ) as reserve, patch(
        "app.services.ai_service.finalize_ai_call",
        side_effect=RuntimeError("database unavailable"),
    ) as finalize:

        with pytest.raises(
            AIServiceError,
            match="AI usage could not be finalized",
        ):
            list(
                service.stream(
                    db=db,
                    user=user,
                    request=AIRequest(prompt="Hello"),
                )
            )

    assert finalize.call_count == 2
    assert "AI quota reservation cleanup failed" in caplog.text
    assert db.rollback.call_count == 2
    reserve.assert_called_once_with(db, user)

def test_stream_logs_rollback_failure(caplog):
    provider = Mock()
    provider.stream.return_value = iter(["partial"])
    service = AIService(provider)
    db = Mock()
    db.rollback.side_effect = RuntimeError("rollback failed")
    user = make_user()

    with patch(
        "app.services.ai_service.reserve_ai_call"
    ), patch(
        "app.services.ai_service.finalize_ai_call",
        side_effect=RuntimeError("database unavailable"),
    ):
        with pytest.raises(AIServiceError):
            list(service.stream(
                db=db,
                user=user,
                request=AIRequest(prompt="Hello"),
            ))

    assert "AI quota reservation cleanup failed" in caplog.text
    assert "AI database rollback failed during quota cleanup" in caplog.text


import asyncio

from starlette.responses import StreamingResponse


def test_streaming_response_cancels_generator_on_disconnect():
    import asyncio

    from starlette.responses import StreamingResponse

    async def run_test():
        cleanup = asyncio.Event()
        started = asyncio.Event()
        sent_messages = []

        async def body():
            try:
                started.set()
                yield b"first"
                await asyncio.Event().wait()
            finally:
                cleanup.set()

        async def receive():
            await started.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            sent_messages.append(message)

        response = StreamingResponse(body())
        scope = {
            "type": "http",
            "asgi": {"spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/stream",
            "raw_path": b"/stream",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 123),
        }

        await asyncio.wait_for(
            response(scope, receive, send),
            timeout=2,
        )

        assert cleanup.is_set()
        assert any(
            message["type"] == "http.response.start"
            for message in sent_messages
        )

    asyncio.run(run_test())
