import json
import httpx
import pytest

from app.ai.embeddings import EmbeddingError, GeminiEmbeddingProvider
from app.core.config import settings


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_embed_returns_configured_vector(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", 3)

    def handler(request):
        assert request.url.params["key"] == "test-key"
        return httpx.Response(
            200,
            json={"embedding": {"values": [0.1, 0.2, 0.3]}},
        )

    provider = GeminiEmbeddingProvider(make_client(handler))
    assert provider.embed("hello") == [0.1, 0.2, 0.3]
    provider.close()


def test_missing_key_fails_without_request(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    provider = GeminiEmbeddingProvider(make_client(
        lambda request: pytest.fail("Unexpected HTTP request")
    ))
    with pytest.raises(EmbeddingError, match="not configured"):
        provider.embed("hello")
    provider.close()


@pytest.mark.parametrize("status_code", [402, 403, 429])
def test_quota_or_access_failure_fails_closed(monkeypatch, status_code):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    provider = GeminiEmbeddingProvider(make_client(
        lambda request: httpx.Response(status_code)
    ))
    with pytest.raises(EmbeddingError):
        provider.embed("hello")
    provider.close()


def test_empty_text_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    provider = GeminiEmbeddingProvider(make_client(
        lambda request: pytest.fail("Unexpected HTTP request")
    ))
    with pytest.raises(EmbeddingError, match="empty"):
        provider.embed("  ")
    provider.close()

@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_embedding_rejects_non_finite_values(monkeypatch, bad_value):
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "gemini_embedding_dimensions", 3)

    provider = GeminiEmbeddingProvider(
        make_client(
            lambda request: httpx.Response(
                200,
                content=json.dumps({"embedding": {"values": [0.1, bad_value, 0.3]}}, allow_nan=True),
            )
        )
    )

    try:
        with pytest.raises(EmbeddingError, match="invalid vector"):
            provider.embed("hello")
    finally:
        provider.close()
