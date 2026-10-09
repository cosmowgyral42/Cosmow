import logging
import time
import uuid

logger = logging.getLogger("cosmow.ai")


def generate_request_id() -> str:
    return uuid.uuid4().hex


def log_ai_call(
    *,
    request_id: str,
    provider: str,
    model: str,
    success: bool,
    duration_ms: float,
) -> None:
    logger.info(
        "ai_call request_id=%s provider=%s model=%s success=%s duration_ms=%.2f",
        request_id,
        provider,
        model,
        success,
        duration_ms,
    )


def log_ai_failure(
    *,
    request_id: str,
    provider: str,
    duration_ms: float,
) -> None:
    logger.warning(
        "ai_call_failed request_id=%s provider=%s duration_ms=%.2f",
        request_id,
        provider,
        duration_ms,
    )


def start_timer() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
