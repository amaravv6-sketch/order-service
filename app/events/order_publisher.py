import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from kafka import KafkaProducer

from app.config import get_settings

logger = logging.getLogger(__name__)


class OrderEventPublisher(Protocol):
    def publish_order_created(
        self,
        *,
        order_id: int,
        product_id: str,
        price: Decimal,
        quantity: int,
        total: Decimal,
    ) -> None:
        ...

    def publish_raw_event(
        self,
        *,
        topic: str,
        key: str,
        value: dict[str, object],
    ) -> None:
        ...


class KafkaOrderEventPublisher:
    def __init__(self) -> None:
        self._producer: KafkaProducer | None = None

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            settings = get_settings()

            self._producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                key_serializer=lambda key: key.encode("utf-8"),
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                retries=3,
                linger_ms=10,
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000,
            )

        return self._producer

    def publish_order_created(
        self,
        *,
        order_id: int,
        product_id: str,
        price: Decimal,
        quantity: int,
        total: Decimal,
    ) -> None:
        settings = get_settings()

        event = {
            "event_id": str(uuid4()),
            "event_type": "OrderCreated",
            "event_version": 1,
            "order_id": order_id,
            "product_id": product_id,
            "price": str(price),
            "quantity": quantity,
            "total": str(total),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        producer = self._get_producer()

        future = producer.send(
            settings.order_created_topic,
            key=str(order_id),
            value=event,
        )

        metadata = future.get(timeout=10)

        logger.info(
            "Published OrderCreated event order_id=%s topic=%s partition=%s offset=%s",
            order_id,
            metadata.topic,
            metadata.partition,
            metadata.offset,
        )



    def publish_raw_event(
        self,
        *,
        topic: str,
        key: str,
        value: dict[str, object],
    ) -> None:
        producer = self._get_producer()

        future = producer.send(
            topic,
            key=key,
            value=value,
        )

        metadata = future.get(timeout=10)

        logger.info(
            "Published raw event topic=%s partition=%s offset=%s key=%s",
            metadata.topic,
            metadata.partition,
            metadata.offset,
            key,
        )


_order_event_publisher = KafkaOrderEventPublisher()

def get_order_event_publisher() -> OrderEventPublisher:
    return _order_event_publisher


