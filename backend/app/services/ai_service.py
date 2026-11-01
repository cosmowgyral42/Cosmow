import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.ai.observability import (
    elapsed_ms,
    generate_request_id,
    log_ai_event,
    start_timer,
)
from app.ai.provider import AIProvider
from app.ai.providers.openrouter import AIProviderRateLimitError
from app.ai.schemas import AIRequest, AIResponse
from app.core.config import settings
from app.models.user import User
from app.services.ai_quota import (
    finalize_ai_call,
    release_ai_call,
    reserve_ai_call,
)


class AIServiceError(Exception):
    """Base exception for AI service failures."""


class AIServiceQuotaError(AIServiceError):
    """The application's own AI usage quota has been exhausted."""


class AIServiceRateLimitError(AIServiceError):
    """The upstream AI provider is rate-limiting requests."""


class AIService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def _log(
        self,
        *,
        level: int,
        event: str,
        request_id: str,
        duration_ms: float,
        error_type: str | None = None,
    ) -> None:
        log_ai_event(
            level=level,
            event=event,
            request_id=request_id,
            provider="openrouter",
            model=settings.ai_model,
            duration_ms=duration_ms,
            error_type=error_type,
        )

    def generate(
        self,
        db: Session,
        user: User,
        request: AIRequest,
        request_id: str | None = None,
    ) -> AIResponse:
        request_id = request_id or generate_request_id()
        started_at = start_timer()

        self._log(
            level=logging.INFO,
            event="ai_request_started",
            request_id=request_id,
            duration_ms=0,
        )

        try:
            reservation = reserve_ai_call(db, user)
        except ValueError as exc:
            self._log(
                level=logging.WARNING,
                event="ai_quota_rejected",
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise AIServiceQuotaError(str(exc)) from exc

        try:
            response = self.provider.generate(request)
        except AIProviderRateLimitError as exc:
            try:
                release_ai_call(db, user, reservation)
            except Exception as cleanup_exc:
                db.rollback()
                self._log(
                    level=logging.ERROR,
                    event="ai_reservation_release_failed",
                    request_id=request_id,
                    duration_ms=elapsed_ms(started_at),
                    error_type=type(cleanup_exc).__name__,
                )

            self._log(
                level=logging.WARNING,
                event="ai_provider_rate_limited",
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise AIServiceRateLimitError(
                "AI provider rate limit reached."
            ) from exc
        except Exception as exc:
            try:
                release_ai_call(db, user, reservation)
            except Exception as cleanup_exc:
                db.rollback()
                self._log(
                    level=logging.ERROR,
                    event="ai_reservation_release_failed",
                    request_id=request_id,
                    duration_ms=elapsed_ms(started_at),
                    error_type=type(cleanup_exc).__name__,
                )

            self._log(
                level=logging.ERROR,
                event="ai_provider_failed",
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise AIServiceError(
                "AI service is temporarily unavailable."
            ) from exc

        try:
            finalize_ai_call(db, user, reservation)
        except Exception as first_exc:
            db.rollback()
            self._log(
                level=logging.WARNING,
                event="ai_usage_finalization_retry",
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
                error_type=type(first_exc).__name__,
            )

            try:
                finalize_ai_call(db, user, reservation)
            except Exception as retry_exc:
                db.rollback()
                self._log(
                    level=logging.ERROR,
                    event="ai_usage_finalization_failed",
                    request_id=request_id,
                    duration_ms=elapsed_ms(started_at),
                    error_type=type(retry_exc).__name__,
                )
                raise AIServiceError(
                    "AI usage could not be finalized."
                ) from retry_exc

        self._log(
            level=logging.INFO,
            event="ai_request_completed",
            request_id=request_id,
            duration_ms=elapsed_ms(started_at),
        )
        return response

    def stream(
        self,
        db: Session,
        user: User,
        request: AIRequest,
        request_id: str | None = None,
    ) -> Iterator[str]:
        request_id = request_id or generate_request_id()
        started_at = start_timer()

        self._log(
            level=logging.INFO,
            event="ai_stream_started",
            request_id=request_id,
            duration_ms=0,
        )

        try:
            reservation = reserve_ai_call(db, user)
        except ValueError as exc:
            self._log(
                level=logging.WARNING,
                event="ai_quota_rejected",
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
                error_type=type(exc).__name__,
            )
            raise AIServiceQuotaError(str(exc)) from exc

        has_content = False
        finalized = False

        try:
            try:
                for chunk in self.provider.stream(request):
                    if chunk:
                        has_content = True
                    yield chunk

            except AIProviderRateLimitError as exc:
                self._log(
                    level=logging.WARNING,
                    event="ai_stream_provider_rate_limited",
                    request_id=request_id,
                    duration_ms=elapsed_ms(started_at),
                    error_type=type(exc).__name__,
                )
                raise AIServiceRateLimitError(
                    "AI provider rate limit reached."
                ) from exc
            except AIServiceError:
                raise
            except Exception as exc:
                self._log(
                    level=logging.ERROR,
                    event="ai_stream_provider_failed",
                    request_id=request_id,
                    duration_ms=elapsed_ms(started_at),
                    error_type=type(exc).__name__,
                )
                raise AIServiceError(
                    "AI service is temporarily unavailable."
                ) from exc

            if has_content:
                try:
                    finalize_ai_call(db, user, reservation)
                    finalized = True
                except Exception as exc:
                    try:
                        db.rollback()
                    except Exception as rollback_exc:
                        self._log(
                            level=logging.ERROR,
                            event="AI database rollback failed after finalization",
                            request_id=request_id,
                            duration_ms=elapsed_ms(started_at),
                            error_type=type(rollback_exc).__name__,
                        )

                    self._log(
                        level=logging.ERROR,
                        event="ai_usage_finalization_failed",
                        request_id=request_id,
                        duration_ms=elapsed_ms(started_at),
                        error_type=type(exc).__name__,
                    )
                    raise AIServiceError(
                        "AI usage could not be finalized."
                    ) from exc
            else:
                release_ai_call(db, user, reservation)

            self._log(
                level=logging.INFO,
                event=(
                    "ai_stream_completed"
                    if has_content
                    else "ai_stream_empty"
                ),
                request_id=request_id,
                duration_ms=elapsed_ms(started_at),
            )

        finally:
            if not finalized:
                try:
                    if has_content:
                        finalize_ai_call(db, user, reservation)
                    else:
                        release_ai_call(db, user, reservation)
                except Exception as cleanup_exc:
                    self._log(
                        level=logging.ERROR,
                        event="AI quota reservation cleanup failed",
                        request_id=request_id,
                        duration_ms=elapsed_ms(started_at),
                        error_type=type(cleanup_exc).__name__,
                    )

                    try:
                        db.rollback()
                    except Exception as rollback_exc:
                        self._log(
                            level=logging.ERROR,
                            event="AI database rollback failed during quota cleanup",
                            request_id=request_id,
                            duration_ms=elapsed_ms(started_at),
                            error_type=type(rollback_exc).__name__,
                        )


def get_ai_service(provider: AIProvider) -> AIService:
    return AIService(provider)
