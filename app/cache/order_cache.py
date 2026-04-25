import json
import logging
from decimal import Decimal
from typing import Any, cast

from redis import Redis

logger = logging.getLogger(__name__)

ORDER_CACHE_TTL_SECONDS = 300


def _order_cache_key(order_id: int) -> str:
    return f"order:{order_id}"


def serialize_order(
    order_id: int,
    product_id: str,
    price: Decimal,
    quantity: int,
    total: Decimal,
) -> str:
    return json.dumps(
        {
            "id": order_id,
            "product_id": product_id,
            "price": str(price),
            "quantity": quantity,
            "total": str(total),
        }
    )


def deserialize_order(payload: str) -> dict[str, Any]:
    data = json.loads(payload)

    if not isinstance(data, dict):
        raise ValueError("Cached order payload must be a JSON object")

    return cast(dict[str, Any], data)


def get_cached_order(redis_client: Redis, order_id: int) -> dict[str, Any] | None:
    key = _order_cache_key(order_id)

    payload = cast(str | None, redis_client.get(key))

    if payload is None:
        logger.info("Cache miss for order_id=%s", order_id)
        return None

    logger.info("Cache hit for order_id=%s", order_id)
    return deserialize_order(payload)


def set_cached_order(
    redis_client: Redis,
    order_id: int,
    product_id: str,
    price: Decimal,
    quantity: int,
    total: Decimal,
) -> None:
    key = _order_cache_key(order_id)

    payload = serialize_order(
        order_id=order_id,
        product_id=product_id,
        price=price,
        quantity=quantity,
        total=total,
    )

    redis_client.setex(
        key,
        ORDER_CACHE_TTL_SECONDS,
        payload,
    )

    logger.info("Cached order_id=%s ttl_seconds=%s", order_id, ORDER_CACHE_TTL_SECONDS)