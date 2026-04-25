import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.repositories.outbox_repository import (
    create_outbox_event,
    list_unpublished_events,
    mark_event_published,
)


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


def test_create_outbox_event_stores_unpublished_event(db_session: Session) -> None:
    payload = {
        "event_id": "event-1",
        "event_type": "OrderCreated",
        "order_id": 1,
    }

    create_outbox_event(
        db=db_session,
        event_id="event-1",
        event_type="OrderCreated",
        topic="orders.created",
        payload=json.dumps(payload),
    )

    db_session.commit()

    events = list_unpublished_events(db=db_session)

    assert len(events) == 1
    assert events[0].event_id == "event-1"
    assert events[0].event_type == "OrderCreated"
    assert events[0].topic == "orders.created"
    assert events[0].published is False


def test_mark_event_published_updates_status(db_session: Session) -> None:
    payload = {
        "event_id": "event-1",
        "event_type": "OrderCreated",
        "order_id": 1,
    }

    event = create_outbox_event(
        db=db_session,
        event_id="event-1",
        event_type="OrderCreated",
        topic="orders.created",
        payload=json.dumps(payload),
    )

    db_session.commit()

    mark_event_published(
        db=db_session,
        outbox_event=event,
    )

    events = list_unpublished_events(db=db_session)

    assert events == []
    assert event.published is True
    assert event.published_at is not None
    
