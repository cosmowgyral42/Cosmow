from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.providers.openrouter import OpenRouterProvider
from app.ai.schemas import AIRequest, AIResponse
from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_db
from app.models.user import User
from app.services.ai_service import AIService, AIServiceError

router = APIRouter(prefix="/ai", tags=["AI"])

ai_service = AIService(
    provider=OpenRouterProvider(),
)


def _handle_ai_error(exc: AIServiceError) -> HTTPException:
    detail = str(exc)

    if "limit" in detail.lower():
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI request limit reached.",
        )

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI service is temporarily unavailable.",
    )


@router.post(
    "/generate",
    response_model=AIResponse,
)
def generate_ai_response(
    request: AIRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return ai_service.generate(
            db=db,
            user=current_user,
            request=request,
        )
    except AIServiceError as exc:
        raise _handle_ai_error(exc) from None


@router.post("/stream")
def stream_ai_response(
    request: AIRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        generator = ai_service.stream(
            db=db,
            user=current_user,
            request=request,
        )

        return StreamingResponse(
            generator,
            media_type="text/plain",
        )

    except AIServiceError as exc:
        raise _handle_ai_error(exc) from None
