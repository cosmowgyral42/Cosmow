import json
from collections.abc import Iterator

import httpx

from app.ai.provider import AIProvider
from app.ai.schemas import AIRequest, AIResponse
from app.core.config import settings


class AIProviderError(Exception):
    """Base exception for AI provider failures."""


class OpenRouterProvider(AIProvider):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.timeout = timeout or settings.openrouter_timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self,
        request: AIRequest,
        stream: bool = False,
    ) -> dict:
        return {
            "model": settings.ai_model,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

    def generate(self, request: AIRequest) -> AIResponse:
        if not self.api_key:
            raise AIProviderError(
                "OpenRouter API key is not configured."
            )

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request),
                timeout=self.timeout,
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                "Unable to reach the AI provider."
            ) from exc

        if response.is_error:
            raise AIProviderError(
                f"OpenRouter request failed with status {response.status_code}."
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                "OpenRouter returned an invalid response."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise AIProviderError(
                "OpenRouter returned an empty response."
            )

        return AIResponse(
            content=content,
            model=data.get("model", settings.ai_model),
            provider="openrouter",
        )

    def stream(self, request: AIRequest) -> Iterator[str]:
        if not self.api_key:
            raise AIProviderError(
                "OpenRouter API key is not configured."
            )

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request, stream=True),
                timeout=self.timeout,
            ) as response:

                if response.is_error:
                    raise AIProviderError(
                        f"OpenRouter request failed with status {response.status_code}."
                    )

                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data = line[5:].strip()

                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])

                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content")

                    if isinstance(content, str) and content:
                        yield content

        except httpx.RequestError as exc:
            raise AIProviderError(
                "Unable to reach the AI provider."
            ) from exc
