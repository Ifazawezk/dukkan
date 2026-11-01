from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, Field, StringConstraints

from app.schemas.common import Money, MoneyIn, PercentIn, Schema


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


Sku = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    Field(pattern=r"^[A-Z0-9._-]{1,40}$"),
]
Barcode = Annotated[
    Annotated[str, StringConstraints(pattern=r"^[0-9A-Za-z-]{4,32}$")] | None,
    BeforeValidator(_blank_to_none),
]


class CategoryOut(Schema):
    id: int
    name: str
    name_ar: str
    product_count: int = 0


class CategoryIn(Schema):
    name: str = Field(min_length=1, max_length=80)
    name_ar: str = Field(default="", max_length=80)


class CategoryUpdate(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    name_ar: str | None = Field(default=None, max_length=80)


class ProductOut(Schema):
    id: int
    sku: str
    barcode: str | None
    name: str
    name_ar: str
    category_id: int | None
    unit: str
    # Hidden (null) for cashiers.
    cost_price: Money | None
    sale_price: Money
    tax_rate: Money | None
    low_stock_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductCreate(Schema):
    sku: Sku
    barcode: Barcode = None
    name: str = Field(min_length=1, max_length=160)
    name_ar: str = Field(default="", max_length=160)
    category_id: int | None = None
    unit: str = Field(default="pcs", min_length=1, max_length=16)
    cost_price: MoneyIn = 0
    sale_price: MoneyIn
    tax_rate: PercentIn | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool = True


class ProductUpdate(Schema):
    sku: Sku | None = None
    barcode: Barcode = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    name_ar: str | None = Field(default=None, max_length=160)
    category_id: int | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=16)
    cost_price: MoneyIn | None = None
    sale_price: MoneyIn | None = None
    tax_rate: PercentIn | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
