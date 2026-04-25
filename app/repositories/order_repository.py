from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OrderModel
from app.repositories.outbox_repository import create_outbox_event
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import get_settings
from app.repositories.outbox_repository import create_outbox_event


def create_order_record(
    db: Session,
    product_id: str,
    price: Decimal,
    quantity: int,
    total: Decimal,
) -> OrderModel:
    order_record = OrderModel(
        product_id=product_id,
        price=price,
        quantity=quantity,
        total=total,
    )

    db.add(order_record)
    db.commit()
    db.refresh(order_record)

    return order_record


def get_order_by_id(db: Session, order_id: int) -> OrderModel | None:
    return db.get(OrderModel, order_id)


def list_orders(
    db: Session,
    product_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    after_id: int | None = None,
) -> list[OrderModel]:
    query = select(OrderModel).order_by(OrderModel.id)

    if product_id is not None:
        query = query.where(OrderModel.product_id == product_id)

    if after_id is not None:
        query = query.where(OrderModel.id > after_id)
    else:
        query = query.offset(offset)

    query = query.limit(limit)

    return list(db.scalars(query).all())


def create_order_record_with_outbox_event(
    db: Session,
    product_id: str,
    price: Decimal,
    quantity: int,
    total: Decimal,
) -> OrderModel:
    settings = get_settings()

    order_record = OrderModel(
        product_id=product_id,
        price=price,
        quantity=quantity,
        total=total,
    )

    db.add(order_record)
    db.flush()

    event_id = str(uuid4())

    event_payload = {
        "event_id": event_id,
        "event_type": "OrderCreated",
        "event_version": 1,
        "order_id": order_record.id,
        "product_id": order_record.product_id,
        "price": str(order_record.price),
        "quantity": order_record.quantity,
        "total": str(order_record.total),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    create_outbox_event(
        db=db,
        event_id=event_id,
        event_type="OrderCreated",
        topic=settings.order_created_topic,
        payload=json.dumps(event_payload),
    )

    db.commit()
    db.refresh(order_record)

    return order_record