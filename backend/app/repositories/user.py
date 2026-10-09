from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def create_user(
    db: Session,
    email: str,
    password_hash: str,
    timezone: str,
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        timezone=timezone,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
