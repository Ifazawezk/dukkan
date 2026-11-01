"""add stock levels and movement ledger

Revision ID: 9349ab8e4be0
Revises: b93dae5108c1
Create Date: 2026-10-30 09:18:29.909920

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9349ab8e4be0"
down_revision: str | None = "b93dae5108c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_levels",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_stock_levels_branch_id_branches")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_stock_levels_product_id_products")
        ),
        sa.PrimaryKeyConstraint("product_id", "branch_id", name=op.f("pk_stock_levels")),
    )
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "purchase",
                "sale",
                "return",
                "adjustment",
                name="movementkind",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.BigInteger(), nullable=True),
        sa.Column(
            "reason",
            sa.Enum(
                "opening_stock",
                "count_correction",
                "damaged",
                "expired",
                "lost",
                "internal_use",
                "other",
                name="adjustmentreason",
                native_enum=False,
                length=20,
            ),
            nullable=True,
        ),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("quantity_change <> 0", name=op.f("ck_stock_movements_nonzero_change")),
        sa.ForeignKeyConstraint(
            ["branch_id"], ["branches.id"], name=op.f("fk_stock_movements_branch_id_branches")
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"], name=op.f("fk_stock_movements_product_id_products")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_stock_movements_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_movements")),
    )
    with op.batch_alter_table("stock_movements", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_stock_movements_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            "ix_stock_movements_product_branch", ["product_id", "branch_id"], unique=False
        )
        batch_op.create_index(
            "ix_stock_movements_reference", ["reference_type", "reference_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("stock_movements", schema=None) as batch_op:
        batch_op.drop_index("ix_stock_movements_reference")
        batch_op.drop_index("ix_stock_movements_product_branch")
        batch_op.drop_index(batch_op.f("ix_stock_movements_created_at"))

    op.drop_table("stock_movements")
    op.drop_table("stock_levels")
