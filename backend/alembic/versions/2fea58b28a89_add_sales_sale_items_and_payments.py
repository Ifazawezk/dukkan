"""add sales, sale items and payments

Revision ID: 2fea58b28a89
Revises: e4e470506cc6
Create Date: 2026-10-30 09:25:34.625798

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2fea58b28a89"
down_revision: str | None = "e4e470506cc6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_no", sa.String(length=30), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("cashier_id", sa.Integer(), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "completed",
                "partially_refunded",
                "refunded",
                name="salestatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("subtotal", sa.BigInteger(), nullable=False),
        sa.Column("discount_total", sa.BigInteger(), nullable=False),
        sa.Column("tax_total", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("amount_tendered", sa.BigInteger(), nullable=False),
        sa.Column("change_due", sa.BigInteger(), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("customer_phone", sa.String(length=30), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_sales_branch_id_branches")
        ),
        sa.ForeignKeyConstraint(
            ["cashier_id"], ["users.id"], name=op.f("fk_sales_cashier_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales")),
        sa.UniqueConstraint("receipt_no", name=op.f("uq_sales_receipt_no")),
    )
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sales_branch_id"), ["branch_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sales_business_date"), ["business_date"], unique=False)
        batch_op.create_index(batch_op.f("ix_sales_cashier_id"), ["cashier_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column(
            "method",
            sa.Enum("cash", "card", "wallet", name="paymentmethod", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("reference", sa.String(length=60), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_payments_amount_positive")),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name=op.f("fk_payments_sale_id_sales"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_payments_sale_id"), ["sale_id"], unique=False)

    op.create_table(
        "sale_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("product_name_ar", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("unit_cost", sa.BigInteger(), nullable=False),
        sa.Column("line_discount", sa.BigInteger(), nullable=False),
        sa.Column("order_discount", sa.BigInteger(), nullable=False),
        sa.Column("tax_rate", sa.BigInteger(), nullable=False),
        sa.Column("tax_amount", sa.BigInteger(), nullable=False),
        sa.Column("line_total", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_sale_items_quantity_positive")),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_sale_items_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name=op.f("fk_sale_items_sale_id_sales"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sale_items")),
    )
    with op.batch_alter_table("sale_items", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sale_items_product_id"), ["product_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sale_items_sale_id"), ["sale_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("sale_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sale_items_sale_id"))
        batch_op.drop_index(batch_op.f("ix_sale_items_product_id"))

    op.drop_table("sale_items")
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_payments_sale_id"))

    op.drop_table("payments")
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sales_cashier_id"))
        batch_op.drop_index(batch_op.f("ix_sales_business_date"))
        batch_op.drop_index(batch_op.f("ix_sales_branch_id"))

    op.drop_table("sales")
