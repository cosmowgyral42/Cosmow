import json
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("cosmow.ai")
logger.setLevel(logging.INFO)
logger.propagate = False

if not any(
    getattr(handler, "_cosmow_json_handler", False)
    for handler in logger.handlers
):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._cosmow_json_handler = True
    logger.addHandler(handler)


def generate_request_id() -> str:
    return uuid.uuid4().hex


def _log_event(level: int, event: str, **fields: object) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        **fields,
    }
    message = json.dumps(payload, separators=(",", ":"))

    if level >= logging.ERROR:
        logger.error(message)
    elif level >= logging.WARNING:
        logger.warning(message)
    else:
        logger.info(message)


def log_ai_call(
    *,
    request_id: str,
    provider: str,
    model: str,
    success: bool,
    duration_ms: float,
) -> None:
    _log_event(
        logging.INFO if success else logging.WARNING,
        "ai_call_succeeded" if success else "ai_call_failed",
        request_id=request_id,
        provider=provider,
        model=model,
        success=success,
        duration_ms=round(duration_ms, 2),
    )


def log_ai_failure(
    *,
    request_id: str,
    provider: str,
    duration_ms: float,
) -> None:
    _log_event(
        logging.WARNING,
        "ai_call_failed",
        request_id=request_id,
        provider=provider,
        duration_ms=round(duration_ms, 2),
    )


def log_ai_event(
    *,
    level: int,
    event: str,
    request_id: str,
    provider: str,
    model: str,
    duration_ms: float,
    error_type: str | None = None,
) -> None:
    fields = {
        "request_id": request_id,
        "provider": provider,
        "model": model,
        "duration_ms": round(duration_ms, 2),
    }
    if error_type:
        fields["error_type"] = error_type

    _log_event(level, event, **fields)


def start_timer() -> float:
    return time.perf_counter()


def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
