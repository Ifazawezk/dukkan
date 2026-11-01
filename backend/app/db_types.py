"""Column types shared by the models.

Money is stored as an integer number of minor units (dirhams for QAR) so that
SQLite and PostgreSQL behave the same and no floating point ever touches a
price. In Python the value is always a ``Decimal``.
"""

import enum
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import BigInteger, DateTime, Enum
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC timestamps and always returns timezone aware values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not allowed, use an aware UTC value")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class FixedDecimal(TypeDecorator[Decimal]):
    """A decimal with a fixed number of places, stored as a scaled integer."""

    impl = BigInteger
    cache_ok = True

    def __init__(self, places: int = 2):
        super().__init__()
        self.places = places
        self._factor = Decimal(10) ** places
        self._quantum = Decimal(1).scaleb(-places)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        scaled = (Decimal(value) * self._factor).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return int(scaled)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (Decimal(value) / self._factor).quantize(self._quantum)


def Money() -> FixedDecimal:  # noqa: N802 - reads like a type in model definitions
    return FixedDecimal(2)


def Percent() -> FixedDecimal:  # noqa: N802
    return FixedDecimal(2)


def str_enum(enum_class: type[enum.Enum], length: int = 20) -> Enum:
    """Store a Python enum as its string value in a plain VARCHAR column."""
    return Enum(
        enum_class,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
    )
