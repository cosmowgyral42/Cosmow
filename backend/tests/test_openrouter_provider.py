import httpx
import pytest

from app.ai.providers.openrouter import AIProviderError, OpenRouterProvider
from app.ai.schemas import AIRequest


def test_openrouter_provider_success(monkeypatch):
    def mock_post(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": "Hello from OpenRouter",
                        }
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OpenRouterProvider(api_key="test-key")

    result = provider.generate(
        AIRequest(prompt="Hello COSMOW")
    )

    assert result.content == "Hello from OpenRouter"
    assert result.model == "test-model"
    assert result.provider == "openrouter"


def test_openrouter_provider_requires_api_key():
    provider = OpenRouterProvider(api_key="")

    with pytest.raises(AIProviderError, match="API key"):
        provider.generate(
            AIRequest(prompt="Hello COSMOW")
        )


def test_openrouter_provider_handles_request_failure(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OpenRouterProvider(api_key="test-key")

    with pytest.raises(
        AIProviderError,
        match="Unable to reach the AI provider",
    ):
        provider.generate(
            AIRequest(prompt="Hello COSMOW")
        )


def test_openrouter_provider_handles_api_error(monkeypatch):
    def mock_post(*args, **kwargs):
        return httpx.Response(
            429,
            json={"error": {"message": "rate limited"}},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OpenRouterProvider(api_key="test-key")

    with pytest.raises(
        AIProviderError,
        match="status 429",
    ):
        provider.generate(
            AIRequest(prompt="Hello COSMOW")
        )


def test_openrouter_provider_handles_invalid_response(monkeypatch):
    def mock_post(*args, **kwargs):
        return httpx.Response(
            200,
            json={"unexpected": "response"},
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OpenRouterProvider(api_key="test-key")

    with pytest.raises(
        AIProviderError,
        match="invalid response",
    ):
        provider.generate(
            AIRequest(prompt="Hello COSMOW")
        )


def test_openrouter_provider_handles_empty_response(monkeypatch):
    def mock_post(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": "",
                        }
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OpenRouterProvider(api_key="test-key")

    with pytest.raises(
        AIProviderError,
        match="empty response",
    ):
        provider.generate(
            AIRequest(prompt="Hello COSMOW")
        )
