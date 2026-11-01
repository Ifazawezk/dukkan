from datetime import datetime

from pydantic import Field, model_validator

from app.models import AdjustmentReason, MovementKind
from app.schemas.common import Money, Schema


class StockRow(Schema):
    product_id: int
    sku: str
    barcode: str | None
    name: str
    name_ar: str
    category_id: int | None
    unit: str
    quantity: int
    low_stock_threshold: int
    is_low: bool
    sale_price: Money
    # Cost based fields are null for cashiers.
    cost_price: Money | None
    stock_value: Money | None


class BranchStock(Schema):
    branch_id: int
    branch_code: str
    branch_name: str
    quantity: int


class MovementOut(Schema):
    id: int
    product_id: int
    sku: str
    product_name: str
    branch_id: int
    kind: MovementKind
    quantity_change: int
    balance_after: int
    unit_cost: Money | None
    reason: AdjustmentReason | None
    reference_type: str | None
    reference_id: int | None
    note: str
    user_id: int | None
    user_name: str | None
    created_at: datetime


class AdjustmentIn(Schema):
    product_id: int
    branch_id: int | None = None
    reason: AdjustmentReason
    quantity_change: int | None = Field(default=None, ge=-100_000, le=100_000)
    counted_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    note: str = Field(default="", max_length=255)

    @model_validator(mode="after")
    def one_kind_of_change(self):
        if (self.quantity_change is None) == (self.counted_quantity is None):
            raise ValueError("send either quantity_change or counted_quantity")
        if self.quantity_change == 0:
            raise ValueError("quantity_change cannot be zero")
        return self


class LedgerProblemOut(Schema):
    product_id: int
    branch_id: int
    problem: str
    stock_level: int
    ledger_total: int


class LedgerCheckOut(Schema):
    ok: bool
    pairs_checked: int
    problems: list[LedgerProblemOut]
