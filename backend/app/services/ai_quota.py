from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_global_usage import AIGlobalUsage
from app.models.ai_usage import AIUsage
from app.models.user import User


def get_user_today(user: User):
    return datetime.now(ZoneInfo(user.timezone)).date()


def get_current_usage(
    db: Session,
    user: User,
) -> AIUsage | None:
    today = get_user_today(user)

    statement = select(AIUsage).where(
        AIUsage.user_id == user.id,
        AIUsage.usage_date == today,
    )

    return db.scalar(statement)


def get_global_usage(
    db: Session,
    user: User,
) -> AIGlobalUsage | None:
    today = get_user_today(user)

    statement = select(AIGlobalUsage).where(
        AIGlobalUsage.usage_date == today,
    )

    return db.scalar(statement)


def check_quota(
    db: Session,
    user: User,
) -> None:
    user_usage = get_current_usage(db, user)

    if (
        user_usage
        and (
            user_usage.request_count
            + user_usage.reserved_count
        ) >= settings.daily_ai_request_limit
    ):
        raise ValueError(
            "Daily AI limit of 5 calls reached. Try again tomorrow."
        )

    global_usage = get_global_usage(db, user)

    if (
        global_usage
        and (
            global_usage.successful_call_count
            + global_usage.reserved_count
        ) >= settings.global_daily_ai_call_limit
    ):
        raise ValueError(
            "Today's global AI capacity of 50 calls has been reached. "
            "AI requests are unavailable until tomorrow."
        )


def reserve_ai_call(
    db: Session,
    user: User,
) -> None:
    today = get_user_today(user)

    # Serialize quota reservations at the database level.
    #
    # The global advisory lock prevents races while creating or
    # updating the global usage row. The user-specific lock protects
    # the per-user quota as well.
    global_lock_key = 900000000

    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": global_lock_key},
    )

    user_lock_key = 1000000 + user.id

    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": user_lock_key},
    )

    user_usage = get_current_usage(db, user)

    if user_usage is None:
        user_usage = AIUsage(
            user_id=user.id,
            usage_date=today,
            request_count=0,
            reserved_count=0,
        )
        db.add(user_usage)
        db.flush()

    global_usage = get_global_usage(db, user)

    if global_usage is None:
        global_usage = AIGlobalUsage(
            usage_date=today,
            successful_call_count=0,
            reserved_count=0,
        )
        db.add(global_usage)
        db.flush()

    user_total = (
        user_usage.request_count
        + user_usage.reserved_count
    )

    if user_total >= settings.daily_ai_request_limit:
        db.rollback()
        raise ValueError(
            "Daily AI limit of 5 calls reached. Try again tomorrow."
        )

    global_total = (
        global_usage.successful_call_count
        + global_usage.reserved_count
    )

    if global_total >= settings.global_daily_ai_call_limit:
        db.rollback()
        raise ValueError(
            "Today's global AI capacity of 50 calls has been reached. "
            "AI requests are unavailable until tomorrow."
        )

    user_usage.reserved_count += 1
    global_usage.reserved_count += 1

    db.commit()


def finalize_ai_call(
    db: Session,
    user: User,
) -> None:
    today = get_user_today(user)

    user_usage = db.scalar(
        select(AIUsage)
        .where(
            AIUsage.user_id == user.id,
            AIUsage.usage_date == today,
        )
        .with_for_update()
    )

    global_usage = db.scalar(
        select(AIGlobalUsage)
        .where(
            AIGlobalUsage.usage_date == today,
        )
        .with_for_update()
    )

    if user_usage is None or global_usage is None:
        raise RuntimeError("AI quota reservation was not found.")

    if user_usage.reserved_count <= 0:
        raise RuntimeError("User AI quota reservation is invalid.")

    if global_usage.reserved_count <= 0:
        raise RuntimeError("Global AI quota reservation is invalid.")

    user_usage.reserved_count -= 1
    user_usage.request_count += 1

    global_usage.reserved_count -= 1
    global_usage.successful_call_count += 1

    db.commit()


def release_ai_call(
    db: Session,
    user: User,
) -> None:
    today = get_user_today(user)

    user_usage = db.scalar(
        select(AIUsage)
        .where(
            AIUsage.user_id == user.id,
            AIUsage.usage_date == today,
        )
        .with_for_update()
    )

    global_usage = db.scalar(
        select(AIGlobalUsage)
        .where(
            AIGlobalUsage.usage_date == today,
        )
        .with_for_update()
    )

    if user_usage is None or global_usage is None:
        raise RuntimeError("AI quota reservation was not found.")

    if user_usage.reserved_count <= 0:
        raise RuntimeError("User AI quota reservation is invalid.")

    if global_usage.reserved_count <= 0:
        raise RuntimeError("Global AI quota reservation is invalid.")

    user_usage.reserved_count -= 1
    global_usage.reserved_count -= 1

    db.commit()


def record_usage(
    db: Session,
    user: User,
) -> tuple[AIUsage, AIGlobalUsage]:
    """
    Compatibility helper for existing tests.

    Successful usage should eventually be recorded through:
        reserve_ai_call()
        finalize_ai_call()

    This function remains temporarily so the existing test suite
    does not break during the concurrency migration.
    """
    reserve_ai_call(db, user)
    finalize_ai_call(db, user)

    user_usage = get_current_usage(db, user)
    global_usage = get_global_usage(db, user)

    if user_usage is None or global_usage is None:
        raise RuntimeError("AI usage records were not found.")

    return user_usage, global_usage
