from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cache.redis_client import get_redis_client
from app.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    settings = get_settings()

    return {
        "status": "alive",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/ready", response_model=None)
def readiness_check(
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> JSONResponse:
    settings = get_settings()

    checks: dict[str, str] = {
        "database": "unknown",
        "redis": "unknown",
    }

    is_ready = True

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"
        is_ready = False

    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "failed"
        is_ready = False

    response_body: dict[str, Any] = {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.app_name,
        "environment": settings.environment,
        "checks": checks,
    }

    status_code = (
        status.HTTP_200_OK
        if is_ready
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=status_code,
        content=response_body,
    )