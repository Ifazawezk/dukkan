from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

# Letters people treat as the same when typing Arabic: alef with or without
# hamza or madda, taa marbuta and haa, alef maqsura and yaa. Tatweel is dropped.
ARABIC_FOLDS = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ـ": ""}


def fold_arabic(text: str) -> str:
    """Spell Arabic the plain way, so أرز, إرز and ارز all read as ارز."""
    for letter, plain in ARABIC_FOLDS.items():
        text = text.replace(letter, plain)
    return text


def folded(column) -> ColumnElement:
    """The same folding done in SQL, for comparing a column with folded input."""
    for letter, plain in ARABIC_FOLDS.items():
        column = func.replace(column, letter, plain)
    return column


def like_pattern(text: str) -> str:
    """Build a 'contains' LIKE pattern with the wildcards in user input escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def count_matching(db: Session, stmt: Select) -> int:
    """Total rows a select would return, ignoring limit, offset and ordering."""
    return db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
