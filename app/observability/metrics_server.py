import logging

from prometheus_client import start_http_server

from app.config import get_settings

logger = logging.getLogger(__name__)

_started = False


def start_worker_metrics_server() -> None:
    global _started

    if _started:
        return

    settings = get_settings()

    if not settings.metrics_server_enabled:
        logger.info("Worker metrics server is disabled")
        return

    start_http_server(settings.metrics_server_port)

    _started = True

    logger.info(
        "Worker metrics server started port=%s",
        settings.metrics_server_port,
    )