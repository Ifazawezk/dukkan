"""Small factories and assertions shared by the tests."""

from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.models import AdjustmentReason, Product, User
from app.services import inventory

_skus = count(1)


def make_product(
    db: Session,
    *,
    name: str = "Test item",
    sale_price: str = "10.00",
    cost_price: str = "6.00",
    category_id: int | None = None,
    tax_rate: str | None = None,
    threshold: int = 5,
) -> Product:
    n = next(_skus)
    product = Product(
        sku=f"T-{n:04d}",
        barcode=f"20{n:011d}",
        name=name,
        sale_price=Decimal(sale_price),
        cost_price=Decimal(cost_price),
        category_id=category_id,
        tax_rate=Decimal(tax_rate) if tax_rate is not None else None,
        low_stock_threshold=threshold,
    )
    db.add(product)
    db.commit()
    return product


def give_stock(db: Session, product: Product, branch_id: int, quantity: int, user: User) -> None:
    inventory.adjust_stock(
        db,
        product=product,
        branch_id=branch_id,
        user=user,
        reason=AdjustmentReason.opening_stock,
        quantity_change=quantity,
    )
    db.commit()


def stock_of(db: Session, product: Product, branch_id: int) -> int:
    db.expire_all()
    return inventory.quantity_on_hand(db, product.id, branch_id)


def assert_ledger_consistent(db: Session) -> None:
    db.expire_all()
    _, problems = inventory.verify_ledger(db)
    assert problems == []
