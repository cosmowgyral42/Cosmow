from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.ai.schemas import AIRequest, AIResponse


class AIProvider(ABC):
    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a complete AI response."""
        raise NotImplementedError

    @abstractmethod
    def stream(self, request: AIRequest) -> Iterator[str]:
        """Stream AI response chunks."""
        raise NotImplementedError
