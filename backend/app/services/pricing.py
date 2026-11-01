"""Cart arithmetic. Pure functions, no database.

Order of operations for every line:

1. gross = unit price x quantity
2. minus the line's own discount
3. minus its share of the order discount (split in proportion to step 2)
4. plus tax on what is left, at the line's tax rate

Everything is rounded to the dirham (0.01 QAR). The order discount is split
with the largest remainder method, so the shares always add up to exactly
the discount the cashier typed in.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.errors import InvalidRequest
from app.models import PaymentMethod
from app.money import ZERO, q


@dataclass(frozen=True)
class LineInput:
    unit_price: Decimal
    quantity: int
    tax_rate: Decimal = ZERO
    discount: Decimal = ZERO


@dataclass(frozen=True)
class PricedLine:
    gross: Decimal
    line_discount: Decimal
    order_discount: Decimal
    net: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class PricedCart:
    lines: list[PricedLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


def to_cents(amount: Decimal) -> int:
    return int(q(amount) * 100)


def from_cents(cents: int) -> Decimal:
    return q(Decimal(cents) / 100)


def allocate(amount_cents: int, weights: list[int]) -> list[int]:
    """Split an amount over weights so the parts add up exactly.

    Every part is at most its exact proportional share rounded up, so no
    part can be bigger than its weight when amount <= sum(weights).
    """
    total_weight = sum(weights)
    if amount_cents == 0 or total_weight == 0:
        return [0] * len(weights)
    exact = [amount_cents * w for w in weights]
    parts = [e // total_weight for e in exact]
    leftover = amount_cents - sum(parts)
    by_remainder = sorted(
        range(len(weights)), key=lambda i: (exact[i] % total_weight, -i), reverse=True
    )
    for i in by_remainder[:leftover]:
        parts[i] += 1
    return parts


def price_cart(lines: list[LineInput], order_discount: Decimal = ZERO) -> PricedCart:
    if not lines:
        raise InvalidRequest("The cart is empty")

    gross = [q(line.unit_price * line.quantity) for line in lines]
    for line, line_gross in zip(lines, gross, strict=True):
        if line.discount < 0 or line.discount > line_gross:
            raise InvalidRequest("A line discount cannot be more than the line amount")
    after_line = [g - line.discount for g, line in zip(gross, lines, strict=True)]

    base = sum(after_line, ZERO)
    if order_discount < 0 or order_discount > base:
        raise InvalidRequest("The order discount cannot be more than the order amount")
    shares = [
        from_cents(c) for c in allocate(to_cents(order_discount), [to_cents(a) for a in after_line])
    ]

    priced = []
    for line, line_gross, amount, share in zip(lines, gross, after_line, shares, strict=True):
        net = amount - share
        tax = q(net * line.tax_rate / 100)
        priced.append(
            PricedLine(
                gross=line_gross,
                line_discount=q(line.discount),
                order_discount=share,
                net=net,
                tax=tax,
                total=net + tax,
            )
        )

    return PricedCart(
        lines=priced,
        subtotal=sum(gross, ZERO),
        discount_total=sum((p.line_discount + p.order_discount for p in priced), ZERO),
        tax_total=sum((p.tax for p in priced), ZERO),
        total=sum((p.total for p in priced), ZERO),
    )


@dataclass(frozen=True)
class PaymentInput:
    method: PaymentMethod
    amount: Decimal
    reference: str = ""


@dataclass(frozen=True)
class Settlement:
    applied: list[PaymentInput]
    tendered: Decimal
    change: Decimal


def settle(total: Decimal, payments: list[PaymentInput]) -> Settlement:
    """Check the payments cover the total and work out the change.

    Only cash can be overpaid; card and wallet payments are for exact amounts.
    The returned payments carry the amount actually applied to the sale, so
    they always add up to the sale total.
    """
    if any(p.amount <= 0 for p in payments):
        raise InvalidRequest("Payment amounts must be positive")
    non_cash = sum((p.amount for p in payments if p.method != PaymentMethod.cash), ZERO)
    if non_cash > total:
        raise InvalidRequest("Card and wallet payments cannot be more than the total")
    tendered = sum((p.amount for p in payments), ZERO)
    if tendered < total:
        raise InvalidRequest(
            "The payment does not cover the total", short_by=float(total - tendered)
        )

    change = tendered - total
    applied = []
    remaining_change = change
    # Take the change back from the last cash payments first.
    for payment in reversed(payments):
        amount = payment.amount
        if payment.method == PaymentMethod.cash and remaining_change > 0:
            taken = min(amount, remaining_change)
            amount -= taken
            remaining_change -= taken
        if amount > 0:
            applied.append(PaymentInput(payment.method, amount, payment.reference))
    applied.reverse()
    return Settlement(applied=applied, tendered=tendered, change=change)
