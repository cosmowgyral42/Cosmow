import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.rate_limit import check_rate_limit

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

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


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()

    client_key = request.client.host if request.client else "unknown"
    retry_after = check_rate_limit(client_key, request.url.path)

    if retry_after is not None:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again shortly."},
            headers={"Retry-After": str(retry_after)},
        )
        _add_security_headers(response, request_id)
        return response

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logging.getLogger("cosmow.http").exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    _add_security_headers(response, request_id)

    logging.getLogger("cosmow.http").info(
        "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    _add_security_headers(response, request_id)
    return response


app.include_router(auth_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
