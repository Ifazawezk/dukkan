from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DbSession, ManagerUser
from app.models import PurchaseOrder, PurchaseOrderStatus
from app.schemas.common import Page
from app.schemas.purchasing import (
    PurchaseItemOut,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseOrderSummary,
    PurchaseOrderUpdate,
    ReceiveIn,
)
from app.services import purchasing
from app.services.queries import count_matching
from app.services.shop import resolve_branch_id

router = APIRouter(prefix="/purchase-orders", tags=["purchasing"])


def summary_fields(po: PurchaseOrder) -> dict:
    return {
        "id": po.id,
        "number": po.number,
        "supplier_id": po.supplier_id,
        "supplier_name": po.supplier.name,
        "branch_id": po.branch_id,
        "status": po.status,
        "expected_date": po.expected_date,
        "created_at": po.created_at,
        "item_count": len(po.items),
        "total_cost": po.total_cost,
    }


def po_out(po: PurchaseOrder) -> PurchaseOrderOut:
    return PurchaseOrderOut(
        **summary_fields(po),
        notes=po.notes,
        created_by_id=po.created_by_id,
        ordered_at=po.ordered_at,
        received_at=po.received_at,
        cancelled_at=po.cancelled_at,
        items=[
            PurchaseItemOut(
                id=item.id,
                product_id=item.product_id,
                sku=item.product.sku,
                product_name=item.product.name,
                product_name_ar=item.product.name_ar,
                quantity_ordered=item.quantity_ordered,
                quantity_received=item.quantity_received,
                unit_cost=item.unit_cost,
                line_total=item.line_total,
            )
            for item in po.items
        ],
    )


def item_lines(items) -> list[purchasing.ItemLine]:
    return [purchasing.ItemLine(i.product_id, i.quantity, i.unit_cost) for i in items]


@router.get("", response_model=Page[PurchaseOrderSummary])
def list_purchase_orders(
    db: DbSession,
    _user: ManagerUser,
    status_filter: PurchaseOrderStatus | None = Query(None, alias="status"),
    supplier_id: int | None = None,
    branch_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[PurchaseOrderSummary]:
    stmt = select(PurchaseOrder)
    if status_filter is not None:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if branch_id is not None:
        stmt = stmt.where(PurchaseOrder.branch_id == branch_id)
    total = count_matching(db, stmt)
    orders = db.scalars(
        stmt.options(selectinload(PurchaseOrder.items), selectinload(PurchaseOrder.supplier))
        .order_by(PurchaseOrder.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return Page(items=[PurchaseOrderSummary(**summary_fields(po)) for po in orders], total=total)


@router.post("", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate, db: DbSession, user: ManagerUser
) -> PurchaseOrderOut:
    po = purchasing.create_purchase_order(
        db,
        supplier_id=payload.supplier_id,
        branch_id=resolve_branch_id(db, user, payload.branch_id),
        lines=item_lines(payload.items),
        user=user,
        expected_date=payload.expected_date,
        notes=payload.notes,
    )
    db.commit()
    return po_out(po)


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(po_id: int, db: DbSession, _user: ManagerUser) -> PurchaseOrderOut:
    return po_out(purchasing.get_purchase_order(db, po_id))


@router.patch("/{po_id}", response_model=PurchaseOrderOut)
def update_purchase_order(
    po_id: int, payload: PurchaseOrderUpdate, db: DbSession, _user: ManagerUser
) -> PurchaseOrderOut:
    po = purchasing.update_draft(
        db,
        purchasing.get_purchase_order(db, po_id),
        supplier_id=payload.supplier_id,
        expected_date=payload.expected_date,
        notes=payload.notes,
        lines=item_lines(payload.items) if payload.items is not None else None,
    )
    db.commit()
    return po_out(po)


@router.post("/{po_id}/submit", response_model=PurchaseOrderOut)
def submit_purchase_order(po_id: int, db: DbSession, _user: ManagerUser) -> PurchaseOrderOut:
    """Mark a draft as sent to the supplier."""
    po = purchasing.submit(purchasing.get_purchase_order(db, po_id))
    db.commit()
    return po_out(po)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderOut)
def cancel_purchase_order(po_id: int, db: DbSession, _user: ManagerUser) -> PurchaseOrderOut:
    po = purchasing.cancel(purchasing.get_purchase_order(db, po_id))
    db.commit()
    return po_out(po)


@router.post("/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(
    po_id: int, payload: ReceiveIn, db: DbSession, user: ManagerUser
) -> PurchaseOrderOut:
    """Book delivered goods into stock. Partial deliveries are fine."""
    po = purchasing.receive(
        db,
        purchasing.get_purchase_order(db, po_id),
        [
            purchasing.ReceiveLine(line.item_id, line.quantity, line.unit_cost)
            for line in payload.lines
        ],
        user=user,
        note=payload.note,
    )
    db.commit()
    return po_out(po)
