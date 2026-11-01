import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.database import engine

router = APIRouter(tags=["health"])
logger = logging.getLogger("cosmow.health")


@router.get("/health/live")
def liveness_check():
    return {"status": "alive"}


@router.get("/health/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(
            "database_readiness_failed",
            extra={
                "event": "database_readiness_failed",
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready"},
        )

    return {"status": "ready"}
