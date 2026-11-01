"""Stock ledger.

Every change to stock goes through ``record_movement``. It appends a row to
``stock_movements`` and updates the running total in ``stock_levels`` in the
same transaction, so the two can never disagree. ``verify_ledger`` checks
that promise and is exposed through the API and the CLI.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db_types import utcnow
from app.errors import InsufficientStock, InvalidRequest
from app.models import (
    AdjustmentReason,
    MovementKind,
    Product,
    StockLevel,
    StockMovement,
    User,
)


def _locked_level(db: Session, product_id: int, branch_id: int) -> StockLevel:
    # FOR UPDATE serialises concurrent sales of the same item on PostgreSQL.
    # SQLite has no row locks and simply ignores it.
    level = db.scalar(
        select(StockLevel)
        .where(StockLevel.product_id == product_id, StockLevel.branch_id == branch_id)
        .with_for_update()
    )
    if level is None:
        level = StockLevel(product_id=product_id, branch_id=branch_id, quantity=0)
        db.add(level)
        db.flush()
    return level


def record_movement(
    db: Session,
    *,
    product: Product,
    branch_id: int,
    change: int,
    kind: MovementKind,
    user: User | None,
    unit_cost: Decimal | None = None,
    reason: AdjustmentReason | None = None,
    reference: tuple[str, int] | None = None,
    note: str = "",
    allow_negative: bool = False,
    at: datetime | None = None,
) -> StockMovement:
    if change == 0:
        raise InvalidRequest("A stock movement must change the quantity")

    level = _locked_level(db, product.id, branch_id)
    new_balance = level.quantity + change
    if change < 0 and new_balance < 0 and not allow_negative:
        raise InsufficientStock(
            f"Not enough stock for {product.name}",
            product_id=product.id,
            sku=product.sku,
            available=level.quantity,
            requested=-change,
        )

    at = at or utcnow()
    level.quantity = new_balance
    level.updated_at = at
    movement = StockMovement(
        product_id=product.id,
        branch_id=branch_id,
        kind=kind,
        quantity_change=change,
        balance_after=new_balance,
        unit_cost=unit_cost,
        reason=reason,
        reference_type=reference[0] if reference else None,
        reference_id=reference[1] if reference else None,
        note=note,
        user_id=user.id if user else None,
        created_at=at,
    )
    db.add(movement)
    return movement


def quantity_on_hand(db: Session, product_id: int, branch_id: int) -> int:
    quantity = db.scalar(
        select(StockLevel.quantity).where(
            StockLevel.product_id == product_id, StockLevel.branch_id == branch_id
        )
    )
    return quantity or 0


def quantities_in_branch(db: Session, branch_id: int, product_ids: list[int]) -> dict[int, int]:
    if not product_ids:
        return {}
    rows = db.execute(
        select(StockLevel.product_id, StockLevel.quantity).where(
            StockLevel.branch_id == branch_id, StockLevel.product_id.in_(product_ids)
        )
    )
    found = dict(rows.all())
    return {product_id: found.get(product_id, 0) for product_id in product_ids}


def total_on_hand(db: Session, product_id: int) -> int:
    total = db.scalar(
        select(func.sum(StockLevel.quantity)).where(StockLevel.product_id == product_id)
    )
    return int(total or 0)


def adjust_stock(
    db: Session,
    *,
    product: Product,
    branch_id: int,
    user: User,
    reason: AdjustmentReason,
    quantity_change: int | None = None,
    counted_quantity: int | None = None,
    note: str = "",
    at: datetime | None = None,
) -> StockMovement:
    """Manual correction: either a signed change or the result of a physical count."""
    if (quantity_change is None) == (counted_quantity is None):
        raise InvalidRequest("Send either quantity_change or counted_quantity")
    if counted_quantity is not None:
        quantity_change = counted_quantity - quantity_on_hand(db, product.id, branch_id)
        if quantity_change == 0:
            raise InvalidRequest("The counted quantity already matches the stock on hand")
    assert quantity_change is not None
    return record_movement(
        db,
        product=product,
        branch_id=branch_id,
        change=quantity_change,
        kind=MovementKind.adjustment,
        user=user,
        unit_cost=product.cost_price,
        reason=reason,
        note=note,
        at=at,
    )


@dataclass
class LedgerProblem:
    product_id: int
    branch_id: int
    problem: str
    stock_level: int
    ledger_total: int


def verify_ledger(db: Session) -> tuple[int, list[LedgerProblem]]:
    """Check stock levels against the movement ledger.

    Returns the number of (product, branch) pairs checked and every problem
    found. Two things must hold for each pair:

    * the stored stock level equals the sum of all its movements, and
    * each movement's ``balance_after`` equals the running sum up to it.
    """
    levels = {
        (p, b): q
        for p, b, q in db.execute(
            select(StockLevel.product_id, StockLevel.branch_id, StockLevel.quantity)
        )
    }

    running: dict[tuple[int, int], int] = defaultdict(int)
    broken_chain: set[tuple[int, int]] = set()
    movements = db.execute(
        select(
            StockMovement.product_id,
            StockMovement.branch_id,
            StockMovement.quantity_change,
            StockMovement.balance_after,
        ).order_by(StockMovement.id)
    )
    for product_id, branch_id, change, balance_after in movements:
        key = (product_id, branch_id)
        running[key] += change
        if running[key] != balance_after:
            broken_chain.add(key)

    problems = []
    for key in sorted(set(levels) | set(running)):
        level, ledger = levels.get(key, 0), running.get(key, 0)
        if level != ledger:
            problems.append(LedgerProblem(*key, "level does not match ledger", level, ledger))
        elif key in broken_chain:
            problems.append(LedgerProblem(*key, "balance_after chain is broken", level, ledger))
    return len(set(levels) | set(running)), problems
