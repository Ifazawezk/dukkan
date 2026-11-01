from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentCounter


def next_number(db: Session, key: str) -> int:
    """Return the next value of a named counter (1, 2, 3, ...).

    The counter row is locked for the rest of the transaction on PostgreSQL,
    so two tills can never hand out the same receipt number.
    """
    counter = db.scalar(select(DocumentCounter).where(DocumentCounter.key == key).with_for_update())
    if counter is None:
        counter = DocumentCounter(key=key, value=0)
        db.add(counter)
    counter.value += 1
    db.flush()
    return counter.value
