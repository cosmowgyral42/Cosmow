from unittest.mock import patch

import httpx
import pytest

from app.ai.providers.openrouter import (
    AIProviderError,
    OpenRouterProvider,
)
from app.ai.schemas import AIRequest


def test_openrouter_timeout_is_handled():
    provider = OpenRouterProvider(api_key="test-key")

    with patch(
        "httpx.post",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        with pytest.raises(
            AIProviderError,
            match="Unable to reach the AI provider",
        ):
            provider.generate(
                AIRequest(prompt="Hello")
            )


def test_openrouter_stream_timeout_is_handled():
    provider = OpenRouterProvider(api_key="test-key")

    with patch(
        "httpx.stream",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        with pytest.raises(
            AIProviderError,
            match="Unable to reach the AI provider",
        ):
            list(
                provider.stream(
                    AIRequest(prompt="Hello")
                )
            )


def test_openrouter_stream_ignores_malformed_chunks():
    provider = OpenRouterProvider(api_key="test-key")

    class FakeResponse:
        is_error = False

        def iter_lines(self):
            yield "data: invalid-json"
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}'
            yield "data: [DONE]"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch(
        "httpx.stream",
        return_value=FakeResponse(),
    ):
        result = list(
            provider.stream(
                AIRequest(prompt="Hello")
            )
        )

    assert result == ["Hello"]


def test_openrouter_stream_handles_http_error():
    provider = OpenRouterProvider(api_key="test-key")

    class FakeResponse:
        is_error = True
        status_code = 429

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch(
        "httpx.stream",
        return_value=FakeResponse(),
    ):
        with pytest.raises(
            AIProviderError,
            match="status 429",
        ):
            list(
                provider.stream(
                    AIRequest(prompt="Hello")
                )
            )
