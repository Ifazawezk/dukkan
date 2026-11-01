import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.db_types import UTCDateTime, utcnow
from app.models.shop import Branch


class Role(enum.StrEnum):
    owner = "owner"
    manager = "manager"
    cashier = "cashier"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20))
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    branch: Mapped[Branch | None] = relationship()

    @property
    def is_manager(self) -> bool:
        return self.role in (Role.owner, Role.manager)
