"""add categories and products

Revision ID: b93dae5108c1
Revises: 487a67936a39
Create Date: 2026-10-30 09:15:50.488966

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b93dae5108c1"
down_revision: str | None = "487a67936a39"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("name_ar", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("barcode", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("name_ar", sa.String(length=160), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("cost_price", sa.BigInteger(), nullable=False),
        sa.Column("sale_price", sa.BigInteger(), nullable=False),
        sa.Column("tax_rate", sa.BigInteger(), nullable=True),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_products_category_id_categories")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("barcode", name=op.f("uq_products_barcode")),
        sa.UniqueConstraint("sku", name=op.f("uq_products_sku")),
    )
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_products_category_id"), ["category_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_products_name"), ["name"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_products_name"))
        batch_op.drop_index(batch_op.f("ix_products_category_id"))

    op.drop_table("products")
    op.drop_table("categories")
