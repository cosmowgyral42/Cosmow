from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.jwt import decode_access_token
from app.core.supabase_jwt import decode_supabase_access_token
from app.models.user import User
from app.repositories.user import get_user_by_id
from app.services.supabase_accounts import (
    SupabaseAccountConflictError,
    provision_supabase_user,
)


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise credentials_exception from None

    algorithm = header.get("alg")

    if algorithm == "HS256":
        # Local tokens are verified only with COSMOW's configured secret.
        try:
            user_id = int(decode_access_token(token))
        except (ValueError, TypeError, jwt.PyJWTError):
            raise credentials_exception from None

        user = get_user_by_id(db, user_id)

        if user is None or not user.is_active:
            raise credentials_exception

        # Prevent a token from another issuer from entering the local path.
        return user

    if algorithm == "ES256":
        try:
            payload = decode_supabase_access_token(token)

            supabase_user_id = UUID(payload["sub"])
            email = payload.get("email")

            if not isinstance(email, str) or not email.strip():
                raise ValueError("Missing Supabase email")

            # Do not provision accounts from unverified or client-supplied data.
            user = provision_supabase_user(
                db=db,
                supabase_user_id=supabase_user_id,
                email=email,
            )
        except SupabaseAccountConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None
        except (ValueError, TypeError, KeyError, jwt.PyJWTError):
            raise credentials_exception from None
        except Exception:
            # Fail closed if JWKS/network/database integration fails.
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            ) from None

        return user

    raise credentials_exception
