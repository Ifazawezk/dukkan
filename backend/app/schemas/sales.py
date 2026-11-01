from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models import PaymentMethod, SaleStatus
from app.schemas.common import Money, MoneyIn, PercentIn, Schema


class CartLineIn(Schema):
    product_id: int
    quantity: int = Field(gt=0, le=10_000)
    discount_amount: MoneyIn | None = None
    discount_percent: PercentIn | None = None

    @model_validator(mode="after")
    def one_discount(self):
        if self.discount_amount is not None and self.discount_percent is not None:
            raise ValueError("use either discount_amount or discount_percent")
        return self


class OrderDiscountIn(Schema):
    type: Literal["amount", "percent"]
    value: MoneyIn

    @model_validator(mode="after")
    def percent_in_range(self):
        if self.type == "percent" and self.value > 100:
            raise ValueError("a percent discount cannot be more than 100")
        return self


class PaymentIn(Schema):
    method: PaymentMethod
    amount: MoneyIn
    reference: str = Field(default="", max_length=60)


class CheckoutIn(Schema):
    branch_id: int | None = None
    items: list[CartLineIn] = Field(min_length=1, max_length=300)
    discount: OrderDiscountIn | None = None
    payments: list[PaymentIn] = Field(default_factory=list, max_length=10)
    customer_name: str = Field(default="", max_length=120)
    customer_phone: str = Field(default="", max_length=30)
    note: str = Field(default="", max_length=255)


class SaleItemOut(Schema):
    id: int
    product_id: int
    sku: str
    product_name: str
    product_name_ar: str
    quantity: int
    unit_price: Money
    line_discount: Money
    order_discount: Money
    tax_rate: Money
    tax_amount: Money
    line_total: Money


class PaymentOut(Schema):
    id: int
    method: PaymentMethod
    amount: Money
    reference: str


class SaleSummary(Schema):
    id: int
    receipt_no: str
    branch_id: int
    cashier_id: int
    cashier_name: str
    business_date: date
    created_at: datetime
    status: SaleStatus
    item_count: int
    total: Money


class SaleOut(SaleSummary):
    branch_name: str
    subtotal: Money
    discount_total: Money
    tax_total: Money
    amount_tendered: Money
    change_due: Money
    customer_name: str
    customer_phone: str
    note: str
    items: list[SaleItemOut]
    payments: list[PaymentOut]
