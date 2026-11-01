"""add sale returns and refund tracking

Revision ID: 0ad1e5c11954
Revises: 2fea58b28a89
Create Date: 2026-10-30 09:28:05.056376

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0ad1e5c11954"
down_revision: str | None = "2fea58b28a89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sale_returns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("return_no", sa.String(length=30), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column(
            "refund_method",
            sa.Enum("cash", "card", "wallet", name="paymentmethod", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("refund_total", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_sale_returns_branch_id_branches")
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name=op.f("fk_sale_returns_sale_id_sales")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sale_returns_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_returns")),
        sa.UniqueConstraint("return_no", name=op.f("uq_sale_returns_return_no")),
    )
    with op.batch_alter_table("sale_returns", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sale_returns_business_date"), ["business_date"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_sale_returns_sale_id"), ["sale_id"], unique=False)

    op.create_table(
        "sale_return_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("return_id", sa.Integer(), nullable=False),
        sa.Column("sale_item_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("refund_amount", sa.BigInteger(), nullable=False),
        sa.Column("tax_amount", sa.BigInteger(), nullable=False),
        sa.Column("cost_amount", sa.BigInteger(), nullable=False),
        sa.Column("restocked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_sale_return_items_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_sale_return_items_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["return_id"],
            ["sale_returns.id"],
            name=op.f("fk_sale_return_items_return_id_sale_returns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"],
            ["sale_items.id"],
            name=op.f("fk_sale_return_items_sale_item_id_sale_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_return_items")),
    )
    with op.batch_alter_table("sale_return_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sale_return_items_return_id"), ["return_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_sale_return_items_sale_item_id"), ["sale_item_id"], unique=False
        )

    with op.batch_alter_table("sale_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("quantity_returned", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("refunded_amount", sa.BigInteger(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("refunded_tax", sa.BigInteger(), server_default="0", nullable=False)
        )
        batch_op.create_check_constraint(
            op.f("ck_sale_items_returned_within_sold"),
            "quantity_returned >= 0 AND quantity_returned <= quantity",
        )

    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("refunded_total", sa.BigInteger(), server_default="0", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.drop_column("refunded_total")

    with op.batch_alter_table("sale_items", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_sale_items_returned_within_sold"), type_="check")
        batch_op.drop_column("refunded_tax")
        batch_op.drop_column("refunded_amount")
        batch_op.drop_column("quantity_returned")

    with op.batch_alter_table("sale_return_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sale_return_items_sale_item_id"))
        batch_op.drop_index(batch_op.f("ix_sale_return_items_return_id"))

    op.drop_table("sale_return_items")
    with op.batch_alter_table("sale_returns", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sale_returns_sale_id"))
        batch_op.drop_index(batch_op.f("ix_sale_returns_business_date"))

    op.drop_table("sale_returns")
