from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.repositories.processed_event_repository import (
    is_event_processed,
    mark_event_processed,
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


def test_mark_event_processed_returns_true_for_new_event(db_session: Session) -> None:
    inserted = mark_event_processed(
        db=db_session,
        event_id="event-1",
        event_type="OrderCreated",
    )

    assert inserted is True
    assert is_event_processed(db_session, "event-1") is True


def test_mark_event_processed_returns_false_for_duplicate_event(
    db_session: Session,
) -> None:
    first_insert = mark_event_processed(
        db=db_session,
        event_id="event-1",
        event_type="OrderCreated",
    )

    second_insert = mark_event_processed(
        db=db_session,
        event_id="event-1",
        event_type="OrderCreated",
    )

    assert first_insert is True
    assert second_insert is False
    assert is_event_processed(db_session, "event-1") is True