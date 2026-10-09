from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.jwt import decode_access_token
from app.repositories.user import get_user_by_id


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        user_id = int(decode_access_token(token))
    except (ValueError, TypeError, jwt.PyJWTError):
        raise credentials_exception from None

    user = get_user_by_id(db, user_id)

    if user is None or not user.is_active:
        raise credentials_exception

    return user
