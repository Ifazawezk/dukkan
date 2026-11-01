from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.models import Role
from app.schemas.common import Password, Schema

Username = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().lower() if isinstance(v, str) else v),
    Field(pattern=r"^[a-z0-9_.-]{3,50}$"),
]


class UserOut(Schema):
    id: int
    username: str
    full_name: str
    role: Role
    branch_id: int | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(Schema):
    username: Username
    full_name: str = Field(min_length=1, max_length=120)
    password: Password
    role: Role
    branch_id: int | None = None


class UserUpdate(Schema):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    branch_id: int | None = None
    is_active: bool | None = None
    password: Password | None = None


class TokenOut(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class ChangePasswordIn(Schema):
    current_password: str
    new_password: Password
