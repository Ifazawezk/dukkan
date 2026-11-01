from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, Field

from app.schemas.common import Money, PercentIn, Schema


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("unknown time zone") from None
    return value


TimeZone = Annotated[str, AfterValidator(_check_timezone)]
BranchCode = Annotated[str, Field(pattern=r"^[A-Z0-9]{2,10}$")]


class BranchOut(Schema):
    id: int
    code: str
    name: str
    name_ar: str
    address: str
    phone: str
    is_active: bool
    created_at: datetime


class BranchCreate(Schema):
    code: BranchCode
    name: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(default="", max_length=120)
    address: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=30)


class BranchUpdate(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    name_ar: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


class ShopSettingsOut(Schema):
    shop_name: str
    shop_name_ar: str
    currency: str
    timezone: str
    default_tax_rate: Money
    allow_negative_stock: bool
    max_cashier_discount_percent: Money
    default_low_stock_threshold: int
    receipt_footer: str
    receipt_footer_ar: str


class ShopSettingsUpdate(Schema):
    shop_name: str | None = Field(default=None, min_length=1, max_length=120)
    shop_name_ar: str | None = Field(default=None, max_length=120)
    timezone: TimeZone | None = None
    default_tax_rate: PercentIn | None = None
    allow_negative_stock: bool | None = None
    max_cashier_discount_percent: PercentIn | None = None
    default_low_stock_threshold: int | None = Field(default=None, ge=0)
    receipt_footer: str | None = Field(default=None, max_length=255)
    receipt_footer_ar: str | None = Field(default=None, max_length=255)
