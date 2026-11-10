import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import check_rate_limit

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.health import router as health_router


class JsonLogFormatter(logging.Formatter):
    """Format application log records as one JSON object per line."""

    SAFE_FIELDS = (
        "event",
        "request_id",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "error_type",
        "retry_after",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in self.SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        return json.dumps(payload, separators=(",", ":"), default=str)


http_logger = logging.getLogger("cosmow.http")
http_logger.setLevel(logging.INFO)
http_logger.propagate = False

if not any(
    getattr(handler, "_cosmow_json_handler", False)
    for handler in http_logger.handlers
):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler._cosmow_json_handler = True
    http_logger.addHandler(handler)


app = FastAPI(
    title="COSMOW",
    version="0.1.0",
)


def _add_security_headers(response, request_id: str) -> None:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )


def _safe_route_name(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else "unmatched"


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    request.state.started_at = time.perf_counter()

    client_key = request.client.host if request.client else "unknown"
    retry_after = check_rate_limit(client_key, request.url.path, request.method)

    if retry_after is not None:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again shortly."},
            headers={"Retry-After": str(retry_after)},
        )
        _add_security_headers(response, request_id)

        http_logger.warning(
            "request_rate_limited",
            extra={
                "event": "request_rate_limited",
                "request_id": request_id,
                "method": request.method,
                "route": _safe_route_name(request),
                "status_code": 429,
                "duration_ms": round(
                    (time.perf_counter() - request.state.started_at) * 1000,
                    2,
                ),
                "retry_after": retry_after,
            },
        )
        return response

    response = await call_next(request)

    duration_ms = (
        time.perf_counter() - request.state.started_at
    ) * 1000

    _add_security_headers(response, request_id)

    event = (
        "request_failed"
        if response.status_code >= 500
        else "request_completed"
    )

    log_method = (
        http_logger.error
        if response.status_code >= 500
        else http_logger.info
    )

    log_method(
        event,
        extra={
            "event": event,
            "request_id": request_id,
            "method": request.method,
            "route": _safe_route_name(request),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(
        request.state,
        "request_id",
        uuid.uuid4().hex,
    )

    started_at = getattr(request.state, "started_at", None)
    duration_ms = (
        round((time.perf_counter() - started_at) * 1000, 2)
        if started_at is not None
        else None
    )

    http_logger.error(
        "request_exception",
        extra={
            "event": "request_exception",
            "request_id": request_id,
            "method": request.method,
            "route": _safe_route_name(request),
            "status_code": 500,
            "duration_ms": duration_ms,
            "error_type": type(exc).__name__,
        },
    )

    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
    _add_security_headers(response, request_id)
    return response


allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(health_router)

