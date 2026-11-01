import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import Money, UTCDateTime, str_enum, utcnow
from app.models.catalog import Product
from app.models.user import User


class MovementKind(enum.StrEnum):
    purchase = "purchase"
    sale = "sale"
    sale_return = "return"
    adjustment = "adjustment"


class AdjustmentReason(enum.StrEnum):
    opening_stock = "opening_stock"
    count_correction = "count_correction"
    damaged = "damaged"
    expired = "expired"
    lost = "lost"
    internal_use = "internal_use"
    other = "other"


class StockLevel(Base):
    """Current quantity of a product in a branch.

    This is a running total of the stock movement ledger, kept in the same
    transaction as every movement. It is never edited on its own; see
    ``app.services.inventory.record_movement``.
    """

    __tablename__ = "stock_levels"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class StockMovement(Base):
    """One line of the stock ledger. Rows are only ever inserted."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity_change <> 0", name="nonzero_change"),
        Index("ix_stock_movements_product_branch", "product_id", "branch_id"),
        Index("ix_stock_movements_reference", "reference_type", "reference_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    kind: Mapped[MovementKind] = mapped_column(str_enum(MovementKind))
    quantity_change: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    unit_cost: Mapped[Decimal | None] = mapped_column(Money())
    reason: Mapped[AdjustmentReason | None] = mapped_column(str_enum(AdjustmentReason))
    reference_type: Mapped[str | None] = mapped_column(String(30))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(255), default="")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    product: Mapped[Product] = relationship()
    user: Mapped[User | None] = relationship()
