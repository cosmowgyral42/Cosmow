from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import (
    get_user_by_email,
    get_user_by_supabase_id,
)


class SupabaseAccountConflictError(Exception):
    """Raised when safe Supabase account provisioning is not possible."""


def provision_supabase_user(
    db: Session,
    supabase_user_id: UUID,
    email: str,
) -> User:
    """Return an existing UUID-mapped user or safely provision a new one.

    Existing local accounts are never linked by email automatically.
    """
    normalized_email = email.strip().lower()

    if not normalized_email:
        raise SupabaseAccountConflictError("Supabase account has no usable email")

    existing_user = get_user_by_supabase_id(db, supabase_user_id)
    if existing_user is not None:
        if not existing_user.is_active:
            raise SupabaseAccountConflictError("Account is inactive")
        return existing_user

    if get_user_by_email(db, normalized_email) is not None:
        raise SupabaseAccountConflictError(
            "Email already belongs to an account; explicit account linking is required"
        )

    # The random password is never returned or sent to the user.
    # Supabase users authenticate through Supabase, not local password login.
    unusable_password_hash = hash_password(str(uuid4()))

    user = User(
        supabase_user_id=supabase_user_id,
        email=normalized_email,
        password_hash=unusable_password_hash,
        timezone="UTC",
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()

        # A concurrent request may have provisioned this UUID first.
        existing_user = get_user_by_supabase_id(db, supabase_user_id)
        if existing_user is not None:
            if not existing_user.is_active:
                raise SupabaseAccountConflictError("Account is inactive")
            return existing_user

        # Another account may have claimed the email concurrently.
        if get_user_by_email(db, normalized_email) is not None:
            raise SupabaseAccountConflictError(
                "Email already belongs to an account; explicit account linking is required"
            )

        raise SupabaseAccountConflictError(
            "Account provisioning failed; please retry"
        ) from None
