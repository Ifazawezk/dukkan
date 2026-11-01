"""Customer returns.

A return refunds part or all of a sale. The refund for a line is its share of
what the customer actually paid (after discounts, with tax), so a discounted
item is never refunded at full price. When the last units of a line come back
the refund is whatever is left of that line, which keeps rounding from
leaking a dirham either way.

Returned goods go back into stock unless they are marked as not restockable
(opened, damaged). Only restocked units reduce the cost of goods sold.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.db_types import utcnow
from app.errors import InvalidRequest, NotFound
from app.models import (
    MovementKind,
    PaymentMethod,
    Sale,
    SaleReturn,
    SaleReturnItem,
    SaleStatus,
    User,
)
from app.money import ZERO, q
from app.services import inventory
from app.services.numbering import next_number
from app.services.shop import business_date, get_shop_settings


@dataclass(frozen=True)
class ReturnLine:
    sale_item_id: int
    quantity: int
    restock: bool = True


def process_return(
    db: Session,
    *,
    sale: Sale,
    lines: list[ReturnLine],
    user: User,
    reason: str = "",
    refund_method: PaymentMethod | None = None,
    at: datetime | None = None,
) -> SaleReturn:
    if not lines:
        raise InvalidRequest("Choose at least one item to return")
    items = {item.id: item for item in sale.items}
    if len({line.sale_item_id for line in lines}) != len(lines):
        raise InvalidRequest("Each sale item can appear only once")

    at = at or utcnow()
    settings = get_shop_settings(db)
    if refund_method is None:
        refund_method = sale.payments[0].method if sale.payments else PaymentMethod.cash

    sale_return = SaleReturn(
        return_no=f"{sale.branch.code}-R{next_number(db, f'return:{sale.branch.code}'):05d}",
        sale_id=sale.id,
        branch_id=sale.branch_id,
        user_id=user.id,
        business_date=business_date(settings, at),
        created_at=at,
        reason=reason,
        refund_method=refund_method,
        refund_total=ZERO,
    )

    for line in lines:
        item = items.get(line.sale_item_id)
        if item is None:
            raise NotFound("Item is not part of this sale", sale_item_id=line.sale_item_id)
        if line.quantity <= 0:
            raise InvalidRequest("Return quantities must be positive", sale_item_id=item.id)
        if line.quantity > item.returnable:
            raise InvalidRequest(
                f"Only {item.returnable} of {item.product_name} can still be returned",
                sale_item_id=item.id,
                returnable=item.returnable,
            )

        if line.quantity == item.returnable:
            refund = item.line_total - item.refunded_amount
            tax = item.tax_amount - item.refunded_tax
        else:
            refund = q(item.line_total * line.quantity / item.quantity)
            tax = q(item.tax_amount * line.quantity / item.quantity)

        item.quantity_returned += line.quantity
        item.refunded_amount += refund
        item.refunded_tax += tax
        sale_return.refund_total += refund
        sale_return.items.append(
            SaleReturnItem(
                sale_item_id=item.id,
                product_id=item.product_id,
                quantity=line.quantity,
                refund_amount=refund,
                tax_amount=tax,
                cost_amount=item.unit_cost * line.quantity if line.restock else ZERO,
                restocked=line.restock,
            )
        )

    sale.refunded_total += sale_return.refund_total
    if all(item.returnable == 0 for item in sale.items):
        sale.status = SaleStatus.refunded
    else:
        sale.status = SaleStatus.partially_refunded

    db.add(sale_return)
    db.flush()

    for return_item in sale_return.items:
        if not return_item.restocked:
            continue
        sale_item = items[return_item.sale_item_id]
        inventory.record_movement(
            db,
            product=sale_item.product,
            branch_id=sale.branch_id,
            change=return_item.quantity,
            kind=MovementKind.sale_return,
            user=user,
            unit_cost=sale_item.unit_cost,
            reference=("sale_return", sale_return.id),
            note=sale_return.return_no,
            at=at,
        )
    return sale_return
