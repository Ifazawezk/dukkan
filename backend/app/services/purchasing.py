"""Purchase orders: draft, order, receive (fully or in parts) or cancel.

Receiving is the only step that touches stock. Each received line becomes a
``purchase`` movement in the ledger and updates the product's moving average
cost, which later feeds the profit and stock valuation reports.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db_types import utcnow
from app.errors import Conflict, InvalidRequest, NotFound
from app.models import (
    MovementKind,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
    User,
)
from app.money import q
from app.services import inventory
from app.services.numbering import next_number

OPEN_STATUSES = (
    PurchaseOrderStatus.draft,
    PurchaseOrderStatus.ordered,
    PurchaseOrderStatus.partially_received,
)


@dataclass
class ItemLine:
    product_id: int
    quantity: int
    unit_cost: Decimal | None = None


@dataclass
class ReceiveLine:
    item_id: int
    quantity: int
    unit_cost: Decimal | None = None


def get_purchase_order(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise NotFound("Purchase order not found", purchase_order_id=po_id)
    return po


def _check_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise NotFound("Supplier not found", supplier_id=supplier_id)
    if not supplier.is_active:
        raise Conflict("This supplier is inactive", supplier_id=supplier_id)
    return supplier


def _build_items(db: Session, lines: list[ItemLine]) -> list[PurchaseOrderItem]:
    if not lines:
        raise InvalidRequest("A purchase order needs at least one item")
    seen: set[int] = set()
    items = []
    for line in lines:
        if line.product_id in seen:
            raise InvalidRequest("Each product can appear only once", product_id=line.product_id)
        seen.add(line.product_id)
        product = db.get(Product, line.product_id)
        if product is None:
            raise NotFound("Product not found", product_id=line.product_id)
        unit_cost = line.unit_cost if line.unit_cost is not None else product.cost_price
        items.append(
            PurchaseOrderItem(
                product_id=product.id,
                quantity_ordered=line.quantity,
                unit_cost=unit_cost,
            )
        )
    return items


def create_purchase_order(
    db: Session,
    *,
    supplier_id: int,
    branch_id: int,
    lines: list[ItemLine],
    user: User | None,
    expected_date: date | None = None,
    notes: str = "",
    at: datetime | None = None,
) -> PurchaseOrder:
    _check_supplier(db, supplier_id)
    po = PurchaseOrder(
        number=f"PO-{next_number(db, 'purchase_order'):05d}",
        supplier_id=supplier_id,
        branch_id=branch_id,
        status=PurchaseOrderStatus.draft,
        expected_date=expected_date,
        notes=notes,
        created_by_id=user.id if user else None,
        created_at=at or utcnow(),
        items=_build_items(db, lines),
    )
    db.add(po)
    db.flush()
    return po


def update_draft(
    db: Session,
    po: PurchaseOrder,
    *,
    supplier_id: int | None = None,
    expected_date: date | None = None,
    notes: str | None = None,
    lines: list[ItemLine] | None = None,
) -> PurchaseOrder:
    if po.status != PurchaseOrderStatus.draft:
        raise Conflict("Only draft purchase orders can be edited", status=po.status)
    if supplier_id is not None:
        _check_supplier(db, supplier_id)
        po.supplier_id = supplier_id
    if expected_date is not None:
        po.expected_date = expected_date
    if notes is not None:
        po.notes = notes
    if lines is not None:
        po.items = _build_items(db, lines)
    db.flush()
    return po


def submit(po: PurchaseOrder, at: datetime | None = None) -> PurchaseOrder:
    if po.status != PurchaseOrderStatus.draft:
        raise Conflict("Only draft purchase orders can be marked as ordered", status=po.status)
    po.status = PurchaseOrderStatus.ordered
    po.ordered_at = at or utcnow()
    return po


def cancel(po: PurchaseOrder, at: datetime | None = None) -> PurchaseOrder:
    if po.status not in (PurchaseOrderStatus.draft, PurchaseOrderStatus.ordered):
        raise Conflict(
            "Only purchase orders with nothing received can be cancelled", status=po.status
        )
    po.status = PurchaseOrderStatus.cancelled
    po.cancelled_at = at or utcnow()
    return po


def moving_average_cost(
    on_hand: int, current_cost: Decimal, quantity: int, unit_cost: Decimal
) -> Decimal:
    """Weighted average of the stock already held and the stock just received."""
    on_hand = max(on_hand, 0)
    if on_hand == 0:
        return q(unit_cost)
    return q((on_hand * current_cost + quantity * unit_cost) / (on_hand + quantity))


def receive(
    db: Session,
    po: PurchaseOrder,
    lines: list[ReceiveLine],
    *,
    user: User | None,
    note: str = "",
    at: datetime | None = None,
) -> PurchaseOrder:
    if po.status not in OPEN_STATUSES:
        raise Conflict("This purchase order can no longer be received", status=po.status)
    if not lines:
        raise InvalidRequest("Nothing to receive")

    items = {item.id: item for item in po.items}
    seen: set[int] = set()
    at = at or utcnow()
    for line in lines:
        item = items.get(line.item_id)
        if item is None:
            raise NotFound("Item is not part of this purchase order", item_id=line.item_id)
        if line.item_id in seen:
            raise InvalidRequest("Each item can appear only once", item_id=line.item_id)
        seen.add(line.item_id)
        if line.quantity <= 0:
            raise InvalidRequest("Received quantity must be positive", item_id=item.id)
        if line.quantity > item.remaining:
            raise InvalidRequest(
                "Cannot receive more than was ordered",
                item_id=item.id,
                remaining=item.remaining,
            )
        if line.unit_cost is not None:
            # The invoice price wins over the price agreed when ordering.
            item.unit_cost = line.unit_cost

        product = item.product
        db.flush()
        product.cost_price = moving_average_cost(
            inventory.total_on_hand(db, product.id),
            product.cost_price,
            line.quantity,
            item.unit_cost,
        )
        inventory.record_movement(
            db,
            product=product,
            branch_id=po.branch_id,
            change=line.quantity,
            kind=MovementKind.purchase,
            user=user,
            unit_cost=item.unit_cost,
            reference=("purchase_order", po.id),
            note=note or po.number,
            at=at,
        )
        item.quantity_received += line.quantity

    if po.ordered_at is None:
        po.ordered_at = at
    if all(item.remaining == 0 for item in po.items):
        po.status = PurchaseOrderStatus.received
        po.received_at = at
    else:
        po.status = PurchaseOrderStatus.partially_received
    db.flush()
    return po
