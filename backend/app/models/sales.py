import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String
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


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

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

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    @property
    def discount(self) -> Decimal:
        return self.line_discount + self.order_discount


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
