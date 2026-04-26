import json
import logging
from typing import Any

from kafka import KafkaConsumer

from app.config import get_settings
from app.logging_config import configure_logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, init_db
from app.repositories.processed_event_repository import (
    is_event_processed,
    mark_event_processed,
)
from app.observability.metrics import (
    KAFKA_EVENTS_PROCESSED_TOTAL,
    KAFKA_EVENTS_SKIPPED_TOTAL,
)

logger = logging.getLogger(__name__)



def process_order_created_event(db: Session, event: dict[str, Any]) -> None:
    event_id = event.get("event_id")

    if not event_id:
        logger.warning(
            "Skipping event without event_id event_type=%s order_id=%s",
            event.get("event_type"),
            event.get("order_id"),
        )
        return

    event_type = event["event_type"]
    order_id = event["order_id"]
    product_id = event["product_id"]
    quantity = event["quantity"]
    total = event["total"]

    if is_event_processed(db, event_id):
        KAFKA_EVENTS_SKIPPED_TOTAL.labels(
        topic="orders.created",
        event_type=event_type,
        ).inc()

        logger.info(
            "Skipping already processed event event_id=%s order_id=%s",
            event_id,
            order_id,
        )
        return

    logger.info(
        "Processing OrderCreated event event_id=%s order_id=%s product_id=%s quantity=%s total=%s",
        event_id,
        order_id,
        product_id,
        quantity,
        total,
    )

    inserted = mark_event_processed(
        db=db,
        event_id=event_id,
        event_type=event_type,
    )

    if not inserted:
        logger.info(
            "Event was already marked processed by another worker event_id=%s order_id=%s",
            event_id,
            order_id,
        )
        return
    KAFKA_EVENTS_PROCESSED_TOTAL.labels(
        topic="orders.created",
        event_type=event_type,
    ).inc()
    logger.info(
        "Marked event as processed event_id=%s order_id=%s",
        event_id,
        order_id,
    )

def run_consumer() -> None:
    configure_logging()
    init_db()

    settings = get_settings()

    consumer = KafkaConsumer(
        settings.order_created_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        group_id="order-created-worker",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        key_deserializer=lambda key: key.decode("utf-8") if key else None,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        consumer_timeout_ms=1000,
        api_version_auto_timeout_ms=5000,
    )

    logger.info(
        "Started Kafka consumer topic=%s group_id=%s",
        settings.order_created_topic,
        "order-created-worker",
    )

    try:
        while True:
            for message in consumer:
                logger.info(
                    "Received Kafka message topic=%s partition=%s offset=%s key=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                    message.key,
                )

                try:
                    with SessionLocal() as db:
                        process_order_created_event(db, message.value)

                    consumer.commit()

                    logger.info(
                        "Committed Kafka offset topic=%s partition=%s offset=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                    )

                except Exception:
                    logger.exception(
                        "Failed to process Kafka message topic=%s partition=%s offset=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                    )
                    raise

    finally:
        consumer.close()
        logger.info("Kafka consumer closed")


if __name__ == "__main__":
    run_consumer()