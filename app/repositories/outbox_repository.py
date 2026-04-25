from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OutboxEventModel


def create_outbox_event(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    topic: str,
    payload: str,
) -> OutboxEventModel:
    event = OutboxEventModel(
        event_id=event_id,
        event_type=event_type,
        topic=topic,
        payload=payload,
        published=False,
    )

    db.add(event)

    return event


def list_unpublished_events(
    db: Session,
    limit: int = 20,
) -> list[OutboxEventModel]:
    query = (
        select(OutboxEventModel)
        .where(OutboxEventModel.published.is_(False))
        .order_by(OutboxEventModel.id)
        .limit(limit)
    )

    return list(db.scalars(query).all())


def mark_event_published(
    db: Session,
    outbox_event: OutboxEventModel,
) -> None:
    outbox_event.published = True
    outbox_event.published_at = datetime.now(timezone.utc)

    db.add(outbox_event)
    db.commit()