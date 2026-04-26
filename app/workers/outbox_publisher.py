import json
import logging
import time
from typing import Any

from app.db.session import SessionLocal, init_db
from app.events.order_publisher import get_order_event_publisher
from app.logging_config import configure_logging
from app.repositories.outbox_repository import (
    list_unpublished_events,
    mark_event_published,
)
from app.observability.metrics import OUTBOX_EVENTS_PUBLISHED_TOTAL
from app.observability.metrics_server import start_worker_metrics_server

logger = logging.getLogger(__name__)


def publish_pending_outbox_events() -> int:
    publisher = get_order_event_publisher()
    published_count = 0

    with SessionLocal() as db:
        events = list_unpublished_events(db=db, limit=20)

        if not events:
            logger.info("No unpublished outbox events found")
            return 0

        for event in events:
            payload: dict[str, Any] = json.loads(event.payload)
            key = str(payload.get("order_id", event.event_id))

            publisher.publish_raw_event(
                topic=event.topic,
                key=key,
                value=payload,
            )

            mark_event_published(db=db, outbox_event=event)

            logger.info(
                "Marked outbox event as published outbox_id=%s event_id=%s topic=%s",
                event.id,
                event.event_id,
                event.topic,
            )
            OUTBOX_EVENTS_PUBLISHED_TOTAL.labels(
                topic=event.topic,
                event_type=event.event_type,
            ).inc()

            published_count += 1

    return published_count


def run_outbox_publisher() -> None:
    configure_logging()
    init_db()
    start_worker_metrics_server()

    logger.info("Started outbox publisher worker")

    while True:
        try:
            publish_pending_outbox_events()
            time.sleep(5)
        except Exception:
            logger.exception("Outbox publisher failed")
            time.sleep(5)


if __name__ == "__main__":
    run_outbox_publisher()