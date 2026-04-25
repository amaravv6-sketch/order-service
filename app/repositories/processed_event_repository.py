from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ProcessedEventModel


def is_event_processed(db: Session, event_id: str) -> bool:
    return db.get(ProcessedEventModel, event_id) is not None


def mark_event_processed(
    db: Session,
    event_id: str,
    event_type: str,
) -> bool:
    processed_event = ProcessedEventModel(
        event_id=event_id,
        event_type=event_type,
    )

    db.add(processed_event)

    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False