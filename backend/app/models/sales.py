import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import Money, Percent, UTCDateTime, str_enum, utcnow
from app.models.catalog import Product
from app.models.shop import Branch
from app.models.user import User


class SaleStatus(enum.StrEnum):
    completed = "completed"
    partially_refunded = "partially_refunded"
    refunded = "refunded"


class PaymentMethod(enum.StrEnum):
    cash = "cash"
    card = "card"
    wallet = "wallet"  # mobile wallets such as Ooredoo Money or Apple Pay


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(30), unique=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), index=True)
    cashier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # The shop's local calendar day of the sale, used by every daily report.
    business_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    status: Mapped[SaleStatus] = mapped_column(str_enum(SaleStatus), default=SaleStatus.completed)
    subtotal: Mapped[Decimal] = mapped_column(Money())
    discount_total: Mapped[Decimal] = mapped_column(Money())
    tax_total: Mapped[Decimal] = mapped_column(Money())
    total: Mapped[Decimal] = mapped_column(Money())
    amount_tendered: Mapped[Decimal] = mapped_column(Money())
    change_due: Mapped[Decimal] = mapped_column(Money())
    refunded_total: Mapped[Decimal] = mapped_column(
        Money(), default=Decimal("0"), server_default="0"
    )
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    customer_phone: Mapped[str] = mapped_column(String(30), default="")
    note: Mapped[str] = mapped_column(String(255), default="")

    branch: Mapped[Branch] = relationship()
    cashier: Mapped[User] = relationship()
    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", order_by="SaleItem.id"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", order_by="Payment.id"
    )
    returns: Mapped[list["SaleReturn"]] = relationship(
        back_populates="sale", order_by="SaleReturn.id"
    )


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "quantity_returned >= 0 AND quantity_returned <= quantity", name="returned_within_sold"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    # Copies of the product details at the time of sale, so old receipts never change.
    sku: Mapped[str] = mapped_column(String(40))
    product_name: Mapped[str] = mapped_column(String(160))
    product_name_ar: Mapped[str] = mapped_column(String(160), default="")
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Money())
    unit_cost: Mapped[Decimal] = mapped_column(Money())
    line_discount: Mapped[Decimal] = mapped_column(Money())
    order_discount: Mapped[Decimal] = mapped_column(Money())
    tax_rate: Mapped[Decimal] = mapped_column(Percent())
    tax_amount: Mapped[Decimal] = mapped_column(Money())
    line_total: Mapped[Decimal] = mapped_column(Money())
    quantity_returned: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    refunded_amount: Mapped[Decimal] = mapped_column(
        Money(), default=Decimal("0"), server_default="0"
    )
    refunded_tax: Mapped[Decimal] = mapped_column(Money(), default=Decimal("0"), server_default="0")

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    @property
    def discount(self) -> Decimal:
        return self.line_discount + self.order_discount

    @property
    def returnable(self) -> int:
        return self.quantity - self.quantity_returned


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod))
    # The part of the sale this payment covers; cash change is already taken off.
    amount: Mapped[Decimal] = mapped_column(Money())
    reference: Mapped[str] = mapped_column(String(60), default="")

    sale: Mapped[Sale] = relationship(back_populates="payments")


class SaleReturn(Base):
    """Goods brought back by a customer, and the money given back for them."""

    __tablename__ = "sale_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_no: Mapped[str] = mapped_column(String(30), unique=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    business_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    reason: Mapped[str] = mapped_column(String(255), default="")
    refund_method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod))
    refund_total: Mapped[Decimal] = mapped_column(Money())

    sale: Mapped[Sale] = relationship(back_populates="returns")
    user: Mapped[User] = relationship()
    items: Mapped[list["SaleReturnItem"]] = relationship(
        back_populates="sale_return", cascade="all, delete-orphan", order_by="SaleReturnItem.id"
    )


class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(
        ForeignKey("sale_returns.id", ondelete="CASCADE"), index=True
    )
    sale_item_id: Mapped[int] = mapped_column(ForeignKey("sale_items.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    refund_amount: Mapped[Decimal] = mapped_column(Money())
    tax_amount: Mapped[Decimal] = mapped_column(Money())
    # Cost of the units that went back on the shelf; zero for damaged goods.
    cost_amount: Mapped[Decimal] = mapped_column(Money())
    restocked: Mapped[bool] = mapped_column(Boolean)

    sale_return: Mapped[SaleReturn] = relationship(back_populates="items")
    sale_item: Mapped[SaleItem] = relationship()
