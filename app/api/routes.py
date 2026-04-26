from decimal import Decimal
from redis import Redis

from app.cache.order_cache import get_cached_order, set_cached_order
from app.cache.redis_client import get_redis_client

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.order_repository import (
    create_order_record_with_outbox_event,
    get_order_by_id,
    list_orders,
)
from app.services.order_service import CreateOrderRequest, create_order


from typing import Annotated

from app.security.auth import CurrentUser, require_role
from app.observability.metrics import ORDERS_CREATED_TOTAL


router = APIRouter()


class CreateOrderApiRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    price: Decimal = Field(..., gt=0)
    quantity: int = Field(..., gt=0)

    @field_validator("product_id")
    @classmethod
    def product_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("product_id must not be blank")
        return value.strip()


class OrderApiResponse(BaseModel):
    id: int
    product_id: str
    price: Decimal
    quantity: int
    total: Decimal


@router.post(
    "/orders",
    response_model=OrderApiResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order_endpoint(
    request: CreateOrderApiRequest,
    _current_user: Annotated[CurrentUser, Depends(require_role("order_writer"))],
    db: Session = Depends(get_db),
) -> OrderApiResponse:
    order = create_order(
        CreateOrderRequest(
            product_id=request.product_id,
            price=request.price,
            quantity=request.quantity,
        )
    )

    saved_order = create_order_record_with_outbox_event(
        db=db,
        product_id=order.product_id,
        price=order.price,
        quantity=order.quantity,
        total=order.total,
    )
    ORDERS_CREATED_TOTAL.inc()

    return OrderApiResponse(
        id=saved_order.id,
        product_id=saved_order.product_id,
        price=saved_order.price,
        quantity=saved_order.quantity,
        total=saved_order.total,
    )

@router.get(
    "/orders/{order_id}",
    response_model=OrderApiResponse,
    status_code=status.HTTP_200_OK,
)
def get_order_endpoint(
    _current_user: Annotated[CurrentUser, Depends(require_role("order_reader"))],
    order_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    redis_client: Redis = Depends(get_redis_client),
) -> OrderApiResponse:
    cached_order = get_cached_order(redis_client, order_id)

    if cached_order is not None:
        return OrderApiResponse(
            id=cached_order["id"],
            product_id=cached_order["product_id"],
            price=Decimal(cached_order["price"]),
            quantity=cached_order["quantity"],
            total=Decimal(cached_order["total"]),
        )

    saved_order = get_order_by_id(db=db, order_id=order_id)

    if saved_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    set_cached_order(
        redis_client=redis_client,
        order_id=saved_order.id,
        product_id=saved_order.product_id,
        price=saved_order.price,
        quantity=saved_order.quantity,
        total=saved_order.total,
    )

    return OrderApiResponse(
        id=saved_order.id,
        product_id=saved_order.product_id,
        price=saved_order.price,
        quantity=saved_order.quantity,
        total=saved_order.total,
    )


@router.get(
    "/orders",
    response_model=list[OrderApiResponse],
    status_code=status.HTTP_200_OK,
)
def list_orders_endpoint(
    _current_user: Annotated[CurrentUser, Depends(require_role("order_reader"))],
    product_id: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    after_id: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db),
) -> list[OrderApiResponse]:
    if after_id is not None and offset != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use either after_id or offset, not both",
        )

    orders = list_orders(
        db=db,
        product_id=product_id,
        limit=limit,
        offset=offset,
        after_id=after_id,
    )

    return [
        OrderApiResponse(
            id=order.id,
            product_id=order.product_id,
            price=order.price,
            quantity=order.quantity,
            total=order.total,
        )
        for order in orders
    ]

