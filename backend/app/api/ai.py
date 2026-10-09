from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_db
from app.core.config import settings
from app.models.user import User
from app.services.ai_quota import (
    finalize_ai_call,
    get_current_usage,
    release_ai_call,
    reserve_ai_call,
)


router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/test")
def test_ai_request(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        reserve_ai_call(db, current_user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from None

    try:
        # Temporary successful AI operation.
        # Real AI provider integration comes in Phase 2.
        finalize_ai_call(db, current_user)

    except Exception:
        try:
            release_ai_call(db, current_user)
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is temporarily unavailable.",
        ) from None

    usage = get_current_usage(db, current_user)
    current_count = usage.request_count if usage else 0

    remaining_requests = max(
        settings.daily_ai_request_limit - current_count,
        0,
    )

    return {
        "message": "AI request successful",
        "remaining_requests": remaining_requests,
    }
