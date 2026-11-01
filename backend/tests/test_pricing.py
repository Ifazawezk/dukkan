import random
from decimal import Decimal

import pytest

from app.errors import InvalidRequest
from app.models import PaymentMethod
from app.services.pricing import LineInput, PaymentInput, allocate, price_cart, settle

D = Decimal
cash, card, wallet = PaymentMethod.cash, PaymentMethod.card, PaymentMethod.wallet


def test_plain_cart():
    cart = price_cart([LineInput(D("6.50"), 2), LineInput(D("2.00"), 3)])
    assert cart.subtotal == D("19.00")
    assert cart.discount_total == D("0.00")
    assert cart.tax_total == D("0.00")
    assert cart.total == D("19.00")


def test_line_discount_comes_off_that_line():
    cart = price_cart([LineInput(D("10.00"), 2, discount=D("1.50")), LineInput(D("5.00"), 1)])
    assert [line.total for line in cart.lines] == [D("18.50"), D("5.00")]
    assert cart.discount_total == D("1.50")


def test_order_discount_is_split_exactly():
    lines = [LineInput(D("10.00"), 1) for _ in range(3)]
    cart = price_cart(lines, order_discount=D("10.00"))
    shares = [line.order_discount for line in cart.lines]
    assert sum(shares) == D("10.00")
    assert sorted(shares) == [D("3.33"), D("3.33"), D("3.34")]
    assert cart.total == D("20.00")


def test_order_discount_follows_line_amounts():
    cart = price_cart(
        [LineInput(D("30.00"), 1), LineInput(D("10.00"), 1)], order_discount=D("4.00")
    )
    assert [line.order_discount for line in cart.lines] == [D("3.00"), D("1.00")]


def test_tax_is_charged_after_discounts():
    cart = price_cart(
        [LineInput(D("100.00"), 1, tax_rate=D("5")), LineInput(D("50.00"), 1)],
        order_discount=D("15.00"),
    )
    taxed, untaxed = cart.lines
    assert taxed.net == D("90.00")
    assert taxed.tax == D("4.50")
    assert untaxed.tax == D("0.00")
    assert cart.total == D("139.50")


def test_full_discount_gives_zero_total():
    cart = price_cart([LineInput(D("3.75"), 3)], order_discount=D("11.25"))
    assert cart.total == D("0.00")


@pytest.mark.parametrize(
    ("lines", "order_discount"),
    [
        ([LineInput(D("5.00"), 1, discount=D("5.01"))], D("0")),
        ([LineInput(D("5.00"), 1)], D("5.01")),
        ([LineInput(D("5.00"), 1, discount=D("-1"))], D("0")),
        ([], D("0")),
    ],
)
def test_invalid_discounts(lines, order_discount):
    with pytest.raises(InvalidRequest):
        price_cart(lines, order_discount)


@pytest.mark.parametrize("seed", range(20))
def test_allocate_properties(seed):
    rng = random.Random(seed)
    weights = [rng.randint(0, 5000) for _ in range(rng.randint(1, 8))]
    amount = rng.randint(0, sum(weights))
    parts = allocate(amount, weights)
    assert sum(parts) == amount
    assert all(0 <= part <= weight for part, weight in zip(parts, weights, strict=True))


def test_settle_cash_with_change():
    result = settle(D("17.25"), [PaymentInput(cash, D("20.00"))])
    assert result.change == D("2.75")
    assert result.tendered == D("20.00")
    assert result.applied == [PaymentInput(cash, D("17.25"))]


def test_settle_split_payment():
    result = settle(D("100.00"), [PaymentInput(card, D("60.00")), PaymentInput(cash, D("50.00"))])
    assert result.change == D("10.00")
    assert [p.amount for p in result.applied] == [D("60.00"), D("40.00")]
    assert sum(p.amount for p in result.applied) == D("100.00")


def test_settle_drops_cash_that_was_all_change():
    result = settle(D("50.00"), [PaymentInput(wallet, D("50.00")), PaymentInput(cash, D("5.00"))])
    assert result.applied == [PaymentInput(wallet, D("50.00"))]
    assert result.change == D("5.00")


def test_card_cannot_be_overpaid():
    with pytest.raises(InvalidRequest):
        settle(D("10.00"), [PaymentInput(card, D("10.01"))])


def test_short_payment_is_refused():
    with pytest.raises(InvalidRequest) as error:
        settle(D("10.00"), [PaymentInput(cash, D("9.00"))])
    assert error.value.context["short_by"] == 1.0


def test_free_sale_needs_no_payment():
    assert settle(D("0.00"), []).applied == []
