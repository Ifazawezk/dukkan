"""create users branches and shop settings

Revision ID: 487a67936a39
Revises:
Create Date: 2026-10-30 09:12:40.053385

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "487a67936a39"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branches")),
        sa.UniqueConstraint("code", name=op.f("uq_branches_code")),
    )
    op.create_table(
        "shop_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shop_name", sa.String(length=120), nullable=False),
        sa.Column("shop_name_ar", sa.String(length=120), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("default_tax_rate", sa.BigInteger(), nullable=False),
        sa.Column("allow_negative_stock", sa.Boolean(), nullable=False),
        sa.Column("max_cashier_discount_percent", sa.BigInteger(), nullable=False),
        sa.Column("default_low_stock_threshold", sa.Integer(), nullable=False),
        sa.Column("receipt_footer", sa.String(length=255), nullable=False),
        sa.Column("receipt_footer_ar", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shop_settings")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=100), nullable=False),
        sa.Column(
            "role",
            sa.Enum("owner", "manager", "cashier", name="role", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_users_branch_id_branches")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("shop_settings")
    op.drop_table("branches")
