from datetime import date, datetime

from pydantic import Field

from app.models import PurchaseOrderStatus
from app.schemas.common import Money, MoneyIn, Schema

Quantity = Field(gt=0, le=100_000)


class SupplierOut(Schema):
    id: int
    name: str
    contact_name: str
    phone: str
    email: str
    address: str
    notes: str
    is_active: bool
    created_at: datetime


class SupplierIn(Schema):
    name: str = Field(min_length=1, max_length=120)
    contact_name: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120, pattern=r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$")
    address: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=500)


class SupplierUpdate(Schema):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    contact_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(
        default=None, max_length=120, pattern=r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class PurchaseItemIn(Schema):
    product_id: int
    quantity: int = Quantity
    # Defaults to the product's current cost price.
    unit_cost: MoneyIn | None = None


class PurchaseOrderCreate(Schema):
    supplier_id: int
    branch_id: int | None = None
    expected_date: date | None = None
    notes: str = Field(default="", max_length=500)
    items: list[PurchaseItemIn] = Field(min_length=1, max_length=500)


class PurchaseOrderUpdate(Schema):
    supplier_id: int | None = None
    expected_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[PurchaseItemIn] | None = Field(default=None, min_length=1, max_length=500)


class PurchaseItemOut(Schema):
    id: int
    product_id: int
    sku: str
    product_name: str
    product_name_ar: str
    quantity_ordered: int
    quantity_received: int
    unit_cost: Money
    line_total: Money


class PurchaseOrderSummary(Schema):
    id: int
    number: str
    supplier_id: int
    supplier_name: str
    branch_id: int
    status: PurchaseOrderStatus
    expected_date: date | None
    created_at: datetime
    item_count: int
    total_cost: Money


class PurchaseOrderOut(PurchaseOrderSummary):
    notes: str
    created_by_id: int | None
    ordered_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    items: list[PurchaseItemOut]


class ReceiveLineIn(Schema):
    item_id: int
    quantity: int = Quantity
    # Use when the supplier's invoice differs from the ordered price.
    unit_cost: MoneyIn | None = None


class ReceiveIn(Schema):
    lines: list[ReceiveLineIn] = Field(min_length=1, max_length=500)
    note: str = Field(default="", max_length=255)
