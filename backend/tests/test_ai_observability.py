from unittest.mock import patch

from app.ai.observability import (
    elapsed_ms,
    generate_request_id,
    log_ai_call,
    log_ai_failure,
)


def test_request_id_is_unique():
    first = generate_request_id()
    second = generate_request_id()

    assert first != second
    assert len(first) == 32
    assert len(second) == 32


def test_elapsed_ms_is_non_negative():
    import time

    start = time.perf_counter()

    assert elapsed_ms(start) >= 0


def test_ai_call_logging_does_not_include_sensitive_content():
    with patch("app.ai.observability.logger.info") as log:
        log_ai_call(
            request_id="test-request",
            provider="openrouter",
            model="openrouter/free",
            success=True,
            duration_ms=125.5,
        )

    message = log.call_args.args[0]
    values = log.call_args.args[1:]

    rendered = message % values

    assert "openrouter/free" in rendered
    assert "test-request" in rendered
    assert "password" not in rendered.lower()
    assert "api_key" not in rendered.lower()
    assert "prompt" not in rendered.lower()


def test_ai_failure_logging_is_safe():
    with patch("app.ai.observability.logger.warning") as log:
        log_ai_failure(
            request_id="test-request",
            provider="openrouter",
            duration_ms=250.0,
        )

    message = log.call_args.args[0]
    values = log.call_args.args[1:]

    rendered = message % values

    assert "test-request" in rendered
    assert "openrouter" in rendered
    assert "api_key" not in rendered.lower()
