import math
import httpx

from app.core.config import settings


class EmbeddingError(Exception):
    """Safe, user-facing embedding failure."""


class GeminiEmbeddingProvider:
    """Hosted Gemini embeddings; never switches to a paid or local provider."""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            timeout=settings.gemini_embedding_timeout_seconds
        )
        self._owns_client = client is None

    def embed(self, text: str, *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if not settings.gemini_api_key:
            raise EmbeddingError("Embeddings are not configured.")

        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text.")

        if task_type not in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}:
            raise EmbeddingError("Unsupported embedding task.")

        url = self.API_URL.format(model=settings.gemini_embedding_model)
        payload = {
            "model": f"models/{settings.gemini_embedding_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": settings.gemini_embedding_dimensions,
        }

        try:
            response = self.client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
            if response.status_code in (402, 403, 429):
                raise EmbeddingError(
                    "Gemini embedding quota is unavailable. Check the Free Tier quota."
                )
            response.raise_for_status()
            data = response.json()
            values = data["embedding"]["values"]

            if (
                not isinstance(values, list)
                or len(values) != settings.gemini_embedding_dimensions
                or not all(
                    isinstance(value, (int, float)) and math.isfinite(value)
                    for value in values
                )
            ):
                raise EmbeddingError("Embedding provider returned an invalid vector.")

            return [float(value) for value in values]

        except EmbeddingError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError(
                "Embedding service is unavailable. No fallback was attempted."
            ) from exc

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
