from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer

from app.money import q


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _round_money(value: Decimal) -> Decimal:
    if value != q(value):
        raise ValueError("amounts can have at most 2 decimal places")
    return q(value)


# Money goes out as a JSON number and comes in as an exact Decimal.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
MoneyIn = Annotated[Decimal, Field(ge=0, le=Decimal("9999999.99")), AfterValidator(_round_money)]
PercentIn = Annotated[Decimal, Field(ge=0, le=100), AfterValidator(_round_money)]


def _check_password(value: str) -> str:
    # bcrypt only looks at the first 72 bytes; refuse longer input instead of truncating it.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password is too long")
    return value


Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_check_password)]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


def changed_fields(payload: BaseModel, nullable: tuple[str, ...] = ()) -> dict:
    """Fields the client actually sent. Nulls are dropped unless the field may be empty."""
    return {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or key in nullable
    }
