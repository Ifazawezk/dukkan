from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def like_pattern(text: str) -> str:
    """Build a 'contains' LIKE pattern with the wildcards in user input escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def count_matching(db: Session, stmt: Select) -> int:
    """Total rows a select would return, ignoring limit, offset and ordering."""
    return db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
