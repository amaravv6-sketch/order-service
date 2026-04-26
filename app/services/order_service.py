import logging
from dataclasses import dataclass
from decimal import Decimal
from opentelemetry import trace




logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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
    with tracer.start_as_current_span("order_service.create_order") as span:
        span.set_attribute("order.product_id", request.product_id)
        span.set_attribute("order.quantity", request.quantity)

        logger.info("Creating order for product_id=%s", request.product_id)

        if not request.product_id or not request.product_id.strip():
            logger.warning("Invalid order request: empty product_id")
            raise InvalidOrderError("product_id must not be empty")

        product_id = request.product_id.strip()

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
        span.set_attribute("order.total", str(total))

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

