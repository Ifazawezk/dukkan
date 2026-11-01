from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.db_types import Percent, UTCDateTime, utcnow


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    name_ar: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ShopSettings(Base):
    """Single row of shop wide settings (id is always 1)."""

    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_name: Mapped[str] = mapped_column(String(120), default="My Shop")
    shop_name_ar: Mapped[str] = mapped_column(String(120), default="")
    currency: Mapped[str] = mapped_column(String(3), default="QAR")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Qatar")
    # Qatar has no VAT today, so tax is off unless the owner sets a rate.
    default_tax_rate: Mapped[Decimal] = mapped_column(Percent(), default=Decimal("0"))
    allow_negative_stock: Mapped[bool] = mapped_column(Boolean, default=False)
    max_cashier_discount_percent: Mapped[Decimal] = mapped_column(Percent(), default=Decimal("10"))
    default_low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
    receipt_footer: Mapped[str] = mapped_column(
        String(255), default="Thank you for shopping with us"
    )
    receipt_footer_ar: Mapped[str] = mapped_column(String(255), default="شكراً لتسوقكم معنا")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
