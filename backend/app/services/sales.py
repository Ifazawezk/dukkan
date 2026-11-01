"""Checkout: turn a cart into a sale, its payments and its stock movements."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db_types import utcnow
from app.errors import Conflict, InvalidRequest, NotFound, PermissionDenied
from app.models import (
    Branch,
    MovementKind,
    Payment,
    Product,
    Role,
    Sale,
    SaleItem,
    SaleStatus,
    User,
)
from app.money import ZERO, q
from app.services import inventory, pricing
from app.services.numbering import next_number
from app.services.shop import business_date, get_shop_settings


@dataclass(frozen=True)
class CartLine:
    product_id: int
    quantity: int
    discount_amount: Decimal | None = None
    discount_percent: Decimal | None = None


@dataclass(frozen=True)
class OrderDiscount:
    kind: str  # "amount" or "percent"
    value: Decimal


def _order_discount_amount(discount: OrderDiscount | None, base: Decimal) -> Decimal:
    if discount is None:
        return ZERO
    if discount.kind == "percent":
        return q(base * discount.value / 100)
    return q(discount.value)


def checkout(
    db: Session,
    *,
    user: User,
    branch_id: int,
    lines: list[CartLine],
    payments: list[pricing.PaymentInput],
    order_discount: OrderDiscount | None = None,
    customer_name: str = "",
    customer_phone: str = "",
    note: str = "",
    at: datetime | None = None,
) -> Sale:
    if not lines:
        raise InvalidRequest("The cart is empty")
    settings = get_shop_settings(db)
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise NotFound("Branch not found", branch_id=branch_id)

    products: list[Product] = []
    inputs: list[pricing.LineInput] = []
    for line in lines:
        product = db.get(Product, line.product_id)
        if product is None:
            raise NotFound("Product not found", product_id=line.product_id)
        if not product.is_active:
            raise Conflict(f"{product.name} is no longer sold", product_id=product.id)
        if line.quantity <= 0:
            raise InvalidRequest("Quantities must be positive", product_id=product.id)
        gross = q(product.sale_price * line.quantity)
        if line.discount_percent is not None:
            discount = q(gross * line.discount_percent / 100)
        else:
            discount = line.discount_amount or ZERO
        tax_rate = product.tax_rate if product.tax_rate is not None else settings.default_tax_rate
        products.append(product)
        inputs.append(pricing.LineInput(product.sale_price, line.quantity, tax_rate, discount))

    base = sum((q(i.unit_price * i.quantity) - i.discount for i in inputs), ZERO)
    cart = pricing.price_cart(inputs, _order_discount_amount(order_discount, base))

    if user.role == Role.cashier and cart.subtotal > 0:
        discount_percent = cart.discount_total / cart.subtotal * 100
        if discount_percent > settings.max_cashier_discount_percent:
            raise PermissionDenied(
                "This discount needs a manager",
                max_percent=float(settings.max_cashier_discount_percent),
            )

    settlement = pricing.settle(cart.total, payments)

    at = at or utcnow()
    sale = Sale(
        receipt_no=f"{branch.code}-{next_number(db, f'receipt:{branch.code}'):06d}",
        branch_id=branch.id,
        cashier_id=user.id,
        business_date=business_date(settings, at),
        created_at=at,
        status=SaleStatus.completed,
        subtotal=cart.subtotal,
        discount_total=cart.discount_total,
        tax_total=cart.tax_total,
        total=cart.total,
        amount_tendered=settlement.tendered,
        change_due=settlement.change,
        customer_name=customer_name,
        customer_phone=customer_phone,
        note=note,
    )
    for product, line_input, priced in zip(products, inputs, cart.lines, strict=True):
        sale.items.append(
            SaleItem(
                product_id=product.id,
                sku=product.sku,
                product_name=product.name,
                product_name_ar=product.name_ar,
                quantity=line_input.quantity,
                unit_price=product.sale_price,
                unit_cost=product.cost_price,
                line_discount=priced.line_discount,
                order_discount=priced.order_discount,
                tax_rate=line_input.tax_rate,
                tax_amount=priced.tax,
                line_total=priced.total,
            )
        )
    for payment in settlement.applied:
        sale.payments.append(
            Payment(method=payment.method, amount=payment.amount, reference=payment.reference)
        )
    db.add(sale)
    db.flush()

    for product, item in zip(products, sale.items, strict=True):
        inventory.record_movement(
            db,
            product=product,
            branch_id=branch.id,
            change=-item.quantity,
            kind=MovementKind.sale,
            user=user,
            unit_cost=item.unit_cost,
            reference=("sale", sale.id),
            note=sale.receipt_no,
            allow_negative=settings.allow_negative_stock,
            at=at,
        )
    return sale


def get_sale(db: Session, sale_id: int, user: User) -> Sale:
    sale = db.get(Sale, sale_id)
    if sale is None or (user.role == Role.cashier and sale.cashier_id != user.id):
        raise NotFound("Sale not found", sale_id=sale_id)
    return sale
