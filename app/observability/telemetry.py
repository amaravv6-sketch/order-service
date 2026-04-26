import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import get_settings
from app.db.session import engine

logger = logging.getLogger(__name__)

_is_configured = False


def configure_telemetry(app: FastAPI) -> None:
    global _is_configured

    if _is_configured:
        return

    settings = get_settings()

    if not settings.otel_enabled:
        logger.info("OpenTelemetry is disabled")
        return

    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "deployment.environment": settings.environment,
        }
    )

    tracer_provider = TracerProvider(resource=resource)

    if settings.otel_console_exporter_enabled:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()

    _is_configured = True

    logger.info("OpenTelemetry configured")