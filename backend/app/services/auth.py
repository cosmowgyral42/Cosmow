from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.repositories.user import create_user, get_user_by_email
from app.schemas.auth import UserCreate


def register_user(db: Session, user_data: UserCreate):
    existing_user = get_user_by_email(db, user_data.email)

    if existing_user:
        raise ValueError("Email already registered")

    password_hash = hash_password(user_data.password)

    return create_user(
        db=db,
        email=user_data.email,
        password_hash=password_hash,
        timezone=user_data.timezone,
    )


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user
