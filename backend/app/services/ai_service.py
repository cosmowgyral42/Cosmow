from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.ai.provider import AIProvider
from app.ai.schemas import AIRequest, AIResponse
from app.models.user import User
from app.services.ai_quota import (
    finalize_ai_call,
    release_ai_call,
    reserve_ai_call,
)


class AIServiceError(Exception):
    """Base exception for AI service failures."""


class AIService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def generate(
        self,
        db: Session,
        user: User,
        request: AIRequest,
    ) -> AIResponse:
        try:
            reserve_ai_call(db, user)
        except ValueError as exc:
            raise AIServiceError(str(exc)) from exc

        try:
            response = self.provider.generate(request)
        except Exception as exc:
            try:
                release_ai_call(db, user)
            except Exception:
                db.rollback()

            raise AIServiceError(
                "AI service is temporarily unavailable."
            ) from exc

        try:
            finalize_ai_call(db, user)
        except Exception as exc:
            db.rollback()

            raise AIServiceError(
                "AI usage could not be finalized."
            ) from exc

        return response

    def stream(
        self,
        db: Session,
        user: User,
        request: AIRequest,
    ) -> Iterator[str]:
        try:
            reserve_ai_call(db, user)
        except ValueError as exc:
            raise AIServiceError(str(exc)) from exc

        completed = False

        try:
            for chunk in self.provider.stream(request):
                yield chunk

            completed = True

        except Exception as exc:
            try:
                release_ai_call(db, user)
            except Exception:
                db.rollback()

            raise AIServiceError(
                "AI service is temporarily unavailable."
            ) from exc

        finally:
            if completed:
                try:
                    finalize_ai_call(db, user)
                except Exception:
                    db.rollback()
                    raise AIServiceError(
                        "AI usage could not be finalized."
                    )

def get_ai_service(provider: AIProvider) -> AIService:
    return AIService(provider)
