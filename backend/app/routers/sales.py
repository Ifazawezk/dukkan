from datetime import date

from fastapi import APIRouter, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DbSession, ManagerUser
from app.models import Role, Sale, SaleReturn
from app.schemas.common import Page
from app.schemas.sales import (
    CheckoutIn,
    ReturnIn,
    ReturnItemOut,
    ReturnOut,
    SaleOut,
    SaleSummary,
)
from app.services import pricing, returns, sales
from app.services.queries import count_matching, like_pattern
from app.services.receipts import render_text_receipt
from app.services.shop import get_shop_settings, resolve_branch_id

router = APIRouter(prefix="/sales", tags=["sales"])


def summary_fields(sale: Sale) -> dict:
    return {
        "id": sale.id,
        "receipt_no": sale.receipt_no,
        "branch_id": sale.branch_id,
        "cashier_id": sale.cashier_id,
        "cashier_name": sale.cashier.full_name,
        "business_date": sale.business_date,
        "created_at": sale.created_at,
        "status": sale.status,
        "item_count": sum(item.quantity for item in sale.items),
        "total": sale.total,
    }


def return_out(sale_return: SaleReturn) -> ReturnOut:
    names = {item.id: item.product_name for item in sale_return.sale.items}
    return ReturnOut(
        id=sale_return.id,
        return_no=sale_return.return_no,
        sale_id=sale_return.sale_id,
        receipt_no=sale_return.sale.receipt_no,
        branch_id=sale_return.branch_id,
        user_id=sale_return.user_id,
        user_name=sale_return.user.full_name,
        business_date=sale_return.business_date,
        created_at=sale_return.created_at,
        reason=sale_return.reason,
        refund_method=sale_return.refund_method,
        refund_total=sale_return.refund_total,
        items=[
            ReturnItemOut(
                id=item.id,
                sale_item_id=item.sale_item_id,
                product_id=item.product_id,
                product_name=names[item.sale_item_id],
                quantity=item.quantity,
                refund_amount=item.refund_amount,
                restocked=item.restocked,
            )
            for item in sale_return.items
        ],
    )


def sale_out(sale: Sale) -> SaleOut:
    return SaleOut.model_validate(
        {
            **summary_fields(sale),
            "branch_name": sale.branch.name,
            "subtotal": sale.subtotal,
            "discount_total": sale.discount_total,
            "tax_total": sale.tax_total,
            "amount_tendered": sale.amount_tendered,
            "change_due": sale.change_due,
            "customer_name": sale.customer_name,
            "customer_phone": sale.customer_phone,
            "note": sale.note,
            "refunded_total": sale.refunded_total,
            "items": sale.items,
            "payments": sale.payments,
            "returns": [return_out(r) for r in sale.returns],
        }
    )


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(payload: CheckoutIn, db: DbSession, user: CurrentUser) -> SaleOut:
    """Check out a cart: prices it, takes payment and deducts stock in one transaction."""
    sale = sales.checkout(
        db,
        user=user,
        branch_id=resolve_branch_id(db, user, payload.branch_id),
        lines=[
            sales.CartLine(i.product_id, i.quantity, i.discount_amount, i.discount_percent)
            for i in payload.items
        ],
        payments=[pricing.PaymentInput(p.method, p.amount, p.reference) for p in payload.payments],
        order_discount=(
            sales.OrderDiscount(payload.discount.type, payload.discount.value)
            if payload.discount
            else None
        ),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        note=payload.note,
    )
    db.commit()
    return sale_out(sale)


@router.get("", response_model=Page[SaleSummary])
def list_sales(
    db: DbSession,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = None,
    cashier_id: int | None = None,
    q: str | None = Query(None, description="Part of a receipt number"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[SaleSummary]:
    """Sales, newest first. Cashiers only see their own."""
    stmt = select(Sale)
    if user.role == Role.cashier:
        cashier_id = user.id
    if cashier_id is not None:
        stmt = stmt.where(Sale.cashier_id == cashier_id)
    if branch_id is not None:
        stmt = stmt.where(Sale.branch_id == branch_id)
    if date_from is not None:
        stmt = stmt.where(Sale.business_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Sale.business_date <= date_to)
    if q:
        stmt = stmt.where(Sale.receipt_no.ilike(like_pattern(q.strip()), escape="\\"))
    total = count_matching(db, stmt)
    rows = db.scalars(
        stmt.options(selectinload(Sale.items), selectinload(Sale.cashier))
        .order_by(Sale.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return Page(items=[SaleSummary(**summary_fields(s)) for s in rows], total=total)


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: DbSession, user: CurrentUser) -> SaleOut:
    return sale_out(sales.get_sale(db, sale_id, user))


@router.get("/{sale_id}/receipt", response_class=PlainTextResponse)
def get_receipt(sale_id: int, db: DbSession, user: CurrentUser) -> str:
    """The receipt as plain text, ready for an 80 mm thermal printer."""
    sale = sales.get_sale(db, sale_id, user)
    return render_text_receipt(sale, get_shop_settings(db))


@router.post("/{sale_id}/returns", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def create_return(sale_id: int, payload: ReturnIn, db: DbSession, user: ManagerUser) -> ReturnOut:
    """Refund some or all items of a sale and put them back in stock."""
    sale_return = returns.process_return(
        db,
        sale=sales.get_sale(db, sale_id, user),
        lines=[returns.ReturnLine(i.sale_item_id, i.quantity, i.restock) for i in payload.items],
        user=user,
        reason=payload.reason,
        refund_method=payload.refund_method,
    )
    db.commit()
    return return_out(sale_return)


returns_router = APIRouter(prefix="/returns", tags=["sales"])


@returns_router.get("", response_model=Page[ReturnOut])
def list_returns(
    db: DbSession,
    _user: ManagerUser,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ReturnOut]:
    stmt = select(SaleReturn)
    if branch_id is not None:
        stmt = stmt.where(SaleReturn.branch_id == branch_id)
    if date_from is not None:
        stmt = stmt.where(SaleReturn.business_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(SaleReturn.business_date <= date_to)
    total = count_matching(db, stmt)
    rows = db.scalars(stmt.order_by(SaleReturn.id.desc()).limit(limit).offset(offset))
    return Page(items=[return_out(r) for r in rows], total=total)
