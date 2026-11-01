from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_global_usage import AIGlobalUsage
from app.models.ai_usage import AIUsage
from app.models.ai_quota_reservation import (
    AIQuotaReservation as AIQuotaReservationRecord,
)
from app.models.user import User


# Backward-compatible name used by the AI service.
AIQuotaReservation = AIQuotaReservationRecord


def get_user_today(user: User) -> date:
    return datetime.now(ZoneInfo(user.timezone)).date()


def get_global_today() -> date:
    return datetime.now(timezone.utc).date()


def get_current_usage(
    db: Session,
    user: User,
    usage_date: date | None = None,
) -> AIUsage | None:
    today = usage_date if usage_date is not None else get_user_today(user)
    return db.scalar(
        select(AIUsage).where(
            AIUsage.user_id == user.id,
            AIUsage.usage_date == today,
        )
    )


def get_global_usage(
    db: Session,
    user: User | None = None,
    usage_date: date | None = None,
) -> AIGlobalUsage | None:
    today = usage_date if usage_date is not None else get_global_today()
    return db.scalar(
        select(AIGlobalUsage).where(AIGlobalUsage.usage_date == today)
    )


def check_quota(db: Session, user: User) -> None:
    user_usage = get_current_usage(db, user)

    if user_usage and (
        user_usage.request_count + user_usage.reserved_count
    ) >= settings.daily_ai_request_limit:
        raise ValueError(
            f"Daily AI limit of {settings.daily_ai_request_limit} calls reached. "
            "Try again tomorrow."
        )

    global_usage = get_global_usage(db)

    if global_usage and (
        global_usage.successful_call_count + global_usage.reserved_count
    ) >= settings.global_daily_ai_call_limit:
        raise ValueError(
            f"Today's global AI capacity of "
            f"{settings.global_daily_ai_call_limit} calls has been reached. "
            "AI requests are unavailable until tomorrow."
        )


def reserve_ai_call(
    db: Session,
    user: User,
) -> AIQuotaReservationRecord:
    user_today = get_user_today(user)
    global_today = get_global_today()

    try:
        # Serialize reservations to prevent quota oversubscription.
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": 900000000},
        )
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": 1000000 + user.id},
        )

        user_usage = db.scalar(
            select(AIUsage)
            .where(
                AIUsage.user_id == user.id,
                AIUsage.usage_date == user_today,
            )
            .with_for_update()
        )
        if user_usage is None:
            user_usage = AIUsage(
                user_id=user.id,
                usage_date=user_today,
                request_count=0,
                reserved_count=0,
            )
            db.add(user_usage)
            db.flush()

        global_usage = db.scalar(
            select(AIGlobalUsage)
            .where(AIGlobalUsage.usage_date == global_today)
            .with_for_update()
        )

        if global_usage is None:
            global_usage = AIGlobalUsage(
                usage_date=global_today,
                successful_call_count=0,
                reserved_count=0,
            )
            db.add(global_usage)
            db.flush()

        if (
            user_usage.request_count + user_usage.reserved_count
        ) >= settings.daily_ai_request_limit:
            raise ValueError(
                f"Daily AI limit of {settings.daily_ai_request_limit} calls reached. "
                "Try again tomorrow."
            )

        if (
            global_usage.successful_call_count + global_usage.reserved_count
        ) >= settings.global_daily_ai_call_limit:
            raise ValueError(
                f"Today's global AI capacity of "
                f"{settings.global_daily_ai_call_limit} calls has been reached. "
                "AI requests are unavailable until tomorrow."
            )

        user_usage.reserved_count += 1
        global_usage.reserved_count += 1

        reservation = AIQuotaReservationRecord(
            user_id=user.id,
            user_usage_date=user_today,
            global_usage_date=global_today,
            status="reserved",
        )

        db.add(reservation)
        db.flush()
        db.commit()

        return reservation

    except Exception:
        db.rollback()
        raise


def _get_locked_reservation(
    db: Session,
    user: User,
    reservation: AIQuotaReservationRecord,
) -> AIQuotaReservationRecord:
    reservation_id = reservation.id

    record = db.scalar(
        select(AIQuotaReservationRecord)
        .where(
            AIQuotaReservationRecord.id == reservation_id,
            AIQuotaReservationRecord.user_id == user.id,
        )
        .with_for_update()
    )

    if record is None:
        raise RuntimeError("AI quota reservation was not found.")

    return record


def finalize_ai_call(
    db: Session,
    user: User,
    reservation: AIQuotaReservationRecord,
) -> bool:
    try:
        record = _get_locked_reservation(db, user, reservation)

        # A reservation can only be finalized once.
        if record.status != "reserved":
            db.commit()
            return False

        user_usage = db.scalar(
            select(AIUsage)
            .where(
                AIUsage.user_id == user.id,
                AIUsage.usage_date == record.user_usage_date,
            )
            .with_for_update()
        )

        global_usage = db.scalar(
            select(AIGlobalUsage)
            .where(
                AIGlobalUsage.usage_date == record.global_usage_date
            )
            .with_for_update()
        )

        if user_usage is None or global_usage is None:
            raise RuntimeError("AI quota usage records were not found.")

        if user_usage.reserved_count <= 0 or global_usage.reserved_count <= 0:
            raise RuntimeError("AI quota reservation counters are invalid.")

        user_usage.reserved_count -= 1
        user_usage.request_count += 1

        global_usage.reserved_count -= 1
        global_usage.successful_call_count += 1

        record.status = "succeeded"
        record.completed_at = datetime.now(timezone.utc)

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def release_ai_call(
    db: Session,
    user: User,
    reservation: AIQuotaReservationRecord,
) -> bool:
    try:
        record = _get_locked_reservation(db, user, reservation)

        # A reservation can only be released once.
        if record.status != "reserved":
            db.commit()
            return False

        user_usage = db.scalar(
            select(AIUsage)
            .where(
                AIUsage.user_id == user.id,
                AIUsage.usage_date == record.user_usage_date,
            )
            .with_for_update()
        )

        global_usage = db.scalar(
            select(AIGlobalUsage)
            .where(
                AIGlobalUsage.usage_date == record.global_usage_date
            )
            .with_for_update()
        )

        if user_usage is None or global_usage is None:
            raise RuntimeError("AI quota usage records were not found.")

        if user_usage.reserved_count <= 0 or global_usage.reserved_count <= 0:
            raise RuntimeError("AI quota reservation counters are invalid.")

        user_usage.reserved_count -= 1
        global_usage.reserved_count -= 1

        record.status = "released"
        record.completed_at = datetime.now(timezone.utc)

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def record_usage(
    db: Session,
    user: User,
) -> tuple[AIUsage, AIGlobalUsage]:
    reservation = reserve_ai_call(db, user)
    finalize_ai_call(db, user, reservation)

    user_usage = get_current_usage(
        db,
        user,
        reservation.user_usage_date,
    )
    global_usage = get_global_usage(
        db,
        usage_date=reservation.global_usage_date,
    )

    if user_usage is None or global_usage is None:
        raise RuntimeError("AI usage records were not found.")

    return user_usage, global_usage
