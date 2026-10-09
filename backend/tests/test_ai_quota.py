from datetime import date

import pytest

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.ai_quota import (
    check_quota,
    finalize_ai_call,
    get_current_usage,
    get_global_usage,
    get_user_today,
    record_usage,
    release_ai_call,
    reserve_ai_call,
)



@pytest.fixture(autouse=True)
def reset_global_quota():
    db = SessionLocal()

    try:
        from app.models.ai_global_usage import AIGlobalUsage

        row = (
            db.query(AIGlobalUsage)
            .filter(AIGlobalUsage.usage_date == date.today())
            .first()
        )

        if row is not None:
            row.successful_call_count = 0
            row.reserved_count = 0
            db.commit()

    finally:
        db.close()

    yield

    db = SessionLocal()

    try:
        from app.models.ai_global_usage import AIGlobalUsage

        row = (
            db.query(AIGlobalUsage)
            .filter(AIGlobalUsage.usage_date == date.today())
            .first()
        )

        if row is not None:
            row.successful_call_count = 0
            row.reserved_count = 0
            db.commit()

    finally:
        db.close()

def create_user(db, email):
    user = User(
        email=email,
        password_hash="test_hash",
        timezone="UTC",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_first_request_is_allowed(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        check_quota(db, user)
        user_usage, global_usage = record_usage(db, user)

        assert user_usage.request_count == 1
        assert global_usage.successful_call_count >= 1

    finally:
        db.close()


def test_quota_allows_requests_until_limit(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        for _ in range(settings.daily_ai_request_limit):
            check_quota(db, user)
            record_usage(db, user)

        user_usage = get_current_usage(db, user)

        assert user_usage.request_count == settings.daily_ai_request_limit

    finally:
        db.close()


def test_quota_rejects_after_limit(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        for _ in range(settings.daily_ai_request_limit):
            record_usage(db, user)

        try:
            check_quota(db, user)
            assert False, "Expected user quota to be exceeded"
        except ValueError as exc:
            assert str(exc) == (
                "Daily AI limit of 5 calls reached. Try again tomorrow."
            )

    finally:
        db.close()


def test_usage_date_uses_user_timezone(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        user_usage, _ = record_usage(db, user)

        assert user_usage.usage_date == get_user_today(user)

    finally:
        db.close()


def test_users_have_separate_quotas(unique_email):
    db = SessionLocal()

    try:
        user_a = create_user(db, unique_email)

        user_b = create_user(
            db,
            f"{unique_email.split('@')[0]}_b@example.com",
        )

        global_usage = get_global_usage(db, user_a)

        previous_global_count = (
            global_usage.successful_call_count
            if global_usage
            else None
        )

        if global_usage is not None:
            global_usage.successful_call_count = 0
            db.commit()

        record_usage(db, user_a)

        check_quota(db, user_b)

        user_b_usage = get_current_usage(db, user_b)

        assert user_b_usage is None

        if global_usage is not None:
            global_usage.successful_call_count = previous_global_count
            db.commit()

    finally:
        db.close()


def test_global_quota_rejects_after_limit(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        global_usage = get_global_usage(db, user)

        if global_usage is None:
            from app.models.ai_global_usage import AIGlobalUsage

            global_usage = AIGlobalUsage(
                usage_date=get_user_today(user),
                successful_call_count=settings.global_daily_ai_call_limit,
                reserved_count=0,
            )
            db.add(global_usage)
            previous_global_count = None
        else:
            previous_global_count = global_usage.successful_call_count
            global_usage.successful_call_count = (
                settings.global_daily_ai_call_limit
            )

        db.commit()

        try:
            check_quota(db, user)
            assert False, "Expected global quota to be exceeded"
        except ValueError as exc:
            assert str(exc) == (
                "Today's global AI capacity of 50 calls has been reached. "
                "AI requests are unavailable until tomorrow."
            )

        if previous_global_count is None:
            db.delete(global_usage)
        else:
            global_usage.successful_call_count = previous_global_count

        db.commit()

    finally:
        db.close()


def test_failed_ai_call_releases_quota(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        reserve_ai_call(db, user)

        usage = get_current_usage(db, user)

        assert usage.reserved_count == 1
        assert usage.request_count == 0

        release_ai_call(db, user)

        usage = get_current_usage(db, user)

        assert usage.reserved_count == 0
        assert usage.request_count == 0

    finally:
        db.close()


def test_successful_ai_call_consumes_quota(unique_email):
    db = SessionLocal()

    try:
        user = create_user(db, unique_email)

        reserve_ai_call(db, user)

        usage = get_current_usage(db, user)

        assert usage.reserved_count == 1
        assert usage.request_count == 0

        finalize_ai_call(db, user)

        usage = get_current_usage(db, user)

        assert usage.reserved_count == 0
        assert usage.request_count == 1

    finally:
        db.close()


def test_user_quota_never_exceeds_limit_under_concurrency(unique_email):
    import threading

    db = SessionLocal()

    try:
        user = create_user(db, unique_email)
        user_id = user.id
    finally:
        db.close()

    results = []
    results_lock = threading.Lock()

    def attempt_reservation():
        local_db = SessionLocal()

        try:
            local_user = local_db.get(User, user_id)

            try:
                reserve_ai_call(local_db, local_user)

                with results_lock:
                    results.append("reserved")

            except ValueError:
                with results_lock:
                    results.append("rejected")

        finally:
            local_db.close()

    threads = [
        threading.Thread(target=attempt_reservation)
        for _ in range(settings.daily_ai_request_limit + 2)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert results.count("reserved") == settings.daily_ai_request_limit
    assert results.count("rejected") == 2

    cleanup_db = SessionLocal()

    try:
        user = cleanup_db.get(User, user_id)
        usage = get_current_usage(cleanup_db, user)

        assert usage.reserved_count == settings.daily_ai_request_limit

        global_usage = get_global_usage(cleanup_db, user)

        usage.reserved_count = 0

        if global_usage:
            global_usage.reserved_count = max(
                0,
                global_usage.reserved_count
                - settings.daily_ai_request_limit,
            )

        cleanup_db.commit()

    finally:
        cleanup_db.close()


def test_global_quota_never_exceeds_limit(unique_email):
    db = SessionLocal()

    users = []

    try:
        from app.models.ai_global_usage import AIGlobalUsage

        global_usage = get_global_usage(
            db,
            create_user(db, f"{unique_email}_setup@example.com"),
        )

        if global_usage is None:
            global_usage = AIGlobalUsage(
                usage_date=get_user_today(users[0]) if users else get_user_today(
                    create_user(db, f"{unique_email}_date@example.com")
                ),
                successful_call_count=0,
                reserved_count=0,
            )
            db.add(global_usage)
        else:
            global_usage.successful_call_count = 0
            global_usage.reserved_count = 0

        db.commit()

        for index in range(
            settings.global_daily_ai_call_limit
            // settings.daily_ai_request_limit
        ):
            user = create_user(
                db,
                f"{unique_email}_{index}@example.com",
            )
            users.append(user)

        for user in users:
            for _ in range(settings.daily_ai_request_limit):
                reserve_ai_call(db, user)

        global_usage = get_global_usage(db, users[0])

        assert (
            global_usage.reserved_count
            == settings.global_daily_ai_call_limit
        )

        extra_user = create_user(
            db,
            f"{unique_email}_extra@example.com",
        )

        try:
            reserve_ai_call(db, extra_user)
            assert False, "Expected global quota to be exceeded"
        except ValueError as exc:
            assert str(exc) == (
                "Today's global AI capacity of 50 calls has been reached. "
                "AI requests are unavailable until tomorrow."
            )

    finally:
        db.close()
