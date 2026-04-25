from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.cache.redis_client import check_redis_connection

from app.api.error_handlers import invalid_order_exception_handler
from app.api.routes import router
from app.config import get_settings
from app.db.session import init_db
from app.logging_config import configure_logging
from app.middleware import request_context_middleware
from app.services.order_service import InvalidOrderError
from app.api.health import router as health_router
from app.api.routes import router as order_router




configure_logging()

settings = get_settings()




@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    check_redis_connection()
    yield

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.middleware("http")(request_context_middleware)

app.add_exception_handler(
    InvalidOrderError,
    invalid_order_exception_handler,
)

app.include_router(router)
app.include_router(health_router)
app.include_router(order_router)

