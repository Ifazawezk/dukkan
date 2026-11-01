from fastapi import APIRouter, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DbSession, ManagerUser
from app.models import Branch, MovementKind, Product, StockLevel, StockMovement
from app.schemas.common import Page
from app.schemas.inventory import (
    AdjustmentIn,
    BranchStock,
    LedgerCheckOut,
    LedgerProblemOut,
    MovementOut,
    StockRow,
)
from app.services import catalog, inventory
from app.services.shop import resolve_branch_id

router = APIRouter(prefix="/inventory", tags=["inventory"])


def movement_out(movement: StockMovement) -> MovementOut:
    return MovementOut(
        id=movement.id,
        product_id=movement.product_id,
        sku=movement.product.sku,
        product_name=movement.product.name,
        branch_id=movement.branch_id,
        kind=movement.kind,
        quantity_change=movement.quantity_change,
        balance_after=movement.balance_after,
        unit_cost=movement.unit_cost,
        reason=movement.reason,
        reference_type=movement.reference_type,
        reference_id=movement.reference_id,
        note=movement.note,
        user_id=movement.user_id,
        user_name=movement.user.full_name if movement.user else None,
        created_at=movement.created_at,
    )


@router.get("/stock", response_model=Page[StockRow])
def list_stock(
    db: DbSession,
    user: CurrentUser,
    branch_id: int | None = None,
    q: str | None = None,
    category_id: int | None = None,
    low_only: bool = False,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Page[StockRow]:
    """Stock on hand in one branch, with low stock flags."""
    branch_id = resolve_branch_id(db, user, branch_id)
    quantity = func.coalesce(StockLevel.quantity, 0)
    stmt = (
        catalog.search_products(q, category_id)
        .add_columns(quantity.label("quantity"))
        .outerjoin(
            StockLevel,
            and_(StockLevel.product_id == Product.id, StockLevel.branch_id == branch_id),
        )
    )
    if low_only:
        stmt = stmt.where(quantity <= Product.low_stock_threshold)

    total = catalog.count_matching(db, stmt)
    rows = db.execute(stmt.order_by(Product.name).limit(limit).offset(offset))
    items = []
    for product, qty in rows:
        show_cost = user.is_manager
        items.append(
            StockRow(
                product_id=product.id,
                sku=product.sku,
                barcode=product.barcode,
                name=product.name,
                name_ar=product.name_ar,
                category_id=product.category_id,
                unit=product.unit,
                quantity=qty,
                low_stock_threshold=product.low_stock_threshold,
                is_low=qty <= product.low_stock_threshold,
                sale_price=product.sale_price,
                cost_price=product.cost_price if show_cost else None,
                stock_value=product.cost_price * max(qty, 0) if show_cost else None,
            )
        )
    return Page(items=items, total=total)


@router.get("/stock/{product_id}/branches", response_model=list[BranchStock])
def stock_across_branches(product_id: int, db: DbSession, _user: CurrentUser) -> list[BranchStock]:
    catalog.get_product(db, product_id)
    rows = db.execute(
        select(Branch, func.coalesce(StockLevel.quantity, 0))
        .outerjoin(
            StockLevel,
            and_(StockLevel.branch_id == Branch.id, StockLevel.product_id == product_id),
        )
        .where(Branch.is_active.is_(True))
        .order_by(Branch.id)
    )
    return [
        BranchStock(branch_id=b.id, branch_code=b.code, branch_name=b.name, quantity=q)
        for b, q in rows
    ]


@router.get("/movements", response_model=Page[MovementOut])
def list_movements(
    db: DbSession,
    _user: ManagerUser,
    branch_id: int | None = None,
    product_id: int | None = None,
    kind: MovementKind | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[MovementOut]:
    """The stock ledger, newest first."""
    stmt = select(StockMovement)
    if branch_id is not None:
        stmt = stmt.where(StockMovement.branch_id == branch_id)
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if kind is not None:
        stmt = stmt.where(StockMovement.kind == kind)
    total = catalog.count_matching(db, stmt)
    movements = db.scalars(
        stmt.options(selectinload(StockMovement.product), selectinload(StockMovement.user))
        .order_by(StockMovement.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return Page(items=[movement_out(m) for m in movements], total=total)


@router.post("/adjustments", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
def create_adjustment(payload: AdjustmentIn, db: DbSession, user: ManagerUser) -> MovementOut:
    """Correct stock after a count, damage, expiry or loss."""
    branch_id = resolve_branch_id(db, user, payload.branch_id)
    product = catalog.get_product(db, payload.product_id)
    movement = inventory.adjust_stock(
        db,
        product=product,
        branch_id=branch_id,
        user=user,
        reason=payload.reason,
        quantity_change=payload.quantity_change,
        counted_quantity=payload.counted_quantity,
        note=payload.note,
    )
    db.commit()
    return movement_out(movement)


@router.get("/verify", response_model=LedgerCheckOut)
def verify(db: DbSession, _user: ManagerUser) -> LedgerCheckOut:
    """Recompute stock from the ledger and report any mismatch."""
    checked, problems = inventory.verify_ledger(db)
    return LedgerCheckOut(
        ok=not problems,
        pairs_checked=checked,
        problems=[LedgerProblemOut(**vars(p)) for p in problems],
    )
