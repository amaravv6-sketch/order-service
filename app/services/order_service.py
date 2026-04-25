import logging
from dataclasses import dataclass
from decimal import Decimal

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import get_settings
from app.repositories.outbox_repository import create_outbox_event


logger = logging.getLogger(__name__)


class InvalidOrderError(Exception):
    pass


@dataclass(frozen=True)
class CreateOrderRequest:
    product_id: str
    price: Decimal
    quantity: int

@dataclass(frozen=True)
class Order:
    id: int | None
    product_id: str
    price: Decimal
    quantity: int
    total: Decimal


def create_order(request: CreateOrderRequest) -> Order:
    logger.info("Creating order for product_id=%s", request.product_id)

    product_id = request.product_id.strip()

    if not product_id:
        logger.warning("Invalid order request: empty product_id")
        raise InvalidOrderError("product_id must not be empty")

    if request.price <= Decimal("0"):
        logger.warning(
            "Invalid order request: price must be greater than zero, product_id=%s",
            product_id,
        )
        raise InvalidOrderError("price must be greater than zero")

    if request.quantity <= 0:
        logger.warning(
            "Invalid order request: quantity must be greater than zero, product_id=%s",
            product_id,
        )
        raise InvalidOrderError("quantity must be greater than zero")

    total = request.price * request.quantity

    logger.info(
        "Order created successfully for product_id=%s quantity=%s total=%s",
        product_id,
        request.quantity,
        total,
    )

    return Order(
        id=None,
        product_id=product_id,
        price=request.price,
        quantity=request.quantity,
        total=total,
    )

