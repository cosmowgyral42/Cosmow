from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import User
from app.services.supabase_accounts import (
    SupabaseAccountConflictError,
    provision_supabase_user,
)


def test_first_login_creates_supabase_user():
    supabase_id = uuid4()
    email = f"{uuid4().hex}@example.com"
    db = SessionLocal()

    try:
        user = provision_supabase_user(db, supabase_id, email)

        assert user.supabase_user_id == supabase_id
        assert user.email == email
        assert user.is_active is True
        assert user.password_hash
        assert user.timezone == "UTC"
    finally:
        db.rollback()
        db.close()


def test_returning_supabase_user_reuses_existing_mapping():
    supabase_id = uuid4()
    email = f"{uuid4().hex}@example.com"
    db = SessionLocal()

    try:
        first = provision_supabase_user(db, supabase_id, email)
        second = provision_supabase_user(db, supabase_id, email)

        assert second.id == first.id

        users = db.scalars(
            select(User).where(User.supabase_user_id == supabase_id)
        ).all()
        assert len(users) == 1
    finally:
        db.rollback()
        db.close()


def test_existing_local_email_is_not_auto_linked():
    email = f"{uuid4().hex}@example.com"
    db = SessionLocal()

    try:
        local_user = User(
            email=email,
            password_hash="existing-local-password-hash",
            timezone="UTC",
        )
        db.add(local_user)
        db.commit()
        local_id = local_user.id

        with pytest.raises(SupabaseAccountConflictError):
            provision_supabase_user(db, uuid4(), email)

        db.refresh(local_user)
        assert local_user.id == local_id
        assert local_user.supabase_user_id is None
    finally:
        db.rollback()
        db.close()


def test_inactive_mapped_user_is_rejected():
    supabase_id = uuid4()
    email = f"{uuid4().hex}@example.com"
    db = SessionLocal()

    try:
        user = User(
            supabase_user_id=supabase_id,
            email=email,
            password_hash="existing-password-hash",
            is_active=False,
            timezone="UTC",
        )
        db.add(user)
        db.commit()

        with pytest.raises(SupabaseAccountConflictError):
            provision_supabase_user(db, supabase_id, email)
    finally:
        db.rollback()
        db.close()
