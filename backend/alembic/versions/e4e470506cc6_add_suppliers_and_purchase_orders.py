"""add suppliers and purchase orders

Revision ID: e4e470506cc6
Revises: 9349ab8e4be0
Create Date: 2026-10-30 09:22:07.929537

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4e470506cc6"
down_revision: str | None = "9349ab8e4be0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_counters",
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_document_counters")),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("name", name=op.f("uq_suppliers_name")),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "ordered",
                "partially_received",
                "received",
                "cancelled",
                name="purchaseorderstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ordered_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_purchase_orders_branch_id_branches")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], name=op.f("fk_purchase_orders_created_by_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_purchase_orders_supplier_id_suppliers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_orders")),
        sa.UniqueConstraint("number", name=op.f("uq_purchase_orders_number")),
    )
    with op.batch_alter_table("purchase_orders", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_purchase_orders_supplier_id"), ["supplier_id"], unique=False
        )

    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "quantity_ordered > 0", name=op.f("ck_purchase_order_items_ordered_positive")
        ),
        sa.CheckConstraint(
            "quantity_received >= 0 AND quantity_received <= quantity_ordered",
            name=op.f("ck_purchase_order_items_received_within_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_purchase_order_items_product_id_products"),
        ),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_orders.id"],
            name=op.f("fk_purchase_order_items_purchase_order_id_purchase_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_order_items")),
    )
    with op.batch_alter_table("purchase_order_items", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_purchase_order_items_purchase_order_id"),
            ["purchase_order_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("purchase_order_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchase_order_items_purchase_order_id"))

    op.drop_table("purchase_order_items")
    with op.batch_alter_table("purchase_orders", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchase_orders_supplier_id"))

    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
    op.drop_table("document_counters")
