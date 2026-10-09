from collections.abc import Iterator

from app.ai.provider import AIProvider
from app.ai.schemas import AIRequest, AIResponse


class MockAIProvider(AIProvider):
    def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            content=f"Mock response for: {request.prompt}",
            model="mock-model",
            provider="mock",
        )

    def stream(self, request: AIRequest) -> Iterator[str]:
        yield "Mock "
        yield "streaming "
        yield "response"
