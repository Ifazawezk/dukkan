from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Branch, PaymentMethod, Role, Sale, User
from app.security import hash_password
from app.services import pricing, sales
from tests.conftest import bearer
from tests.helpers import assert_ledger_consistent, give_stock, make_product, stock_of


@pytest.fixture
def milk(db, users, branch):
    product = make_product(db, name="Fresh Milk 1L", sale_price="6.50", cost_price="5.10")
    give_stock(db, product, branch.id, 20, users["manager"])
    return product


@pytest.fixture
def bread(db, users, branch):
    product = make_product(db, name="Arabic Bread", sale_price="2.00", cost_price="1.40")
    give_stock(db, product, branch.id, 20, users["manager"])
    return product


def checkout(client, headers, items, payments=None, **extra):
    payload = {"items": items, "payments": payments or [], **extra}
    return client.post("/api/sales", json=payload, headers=headers)


def cash(amount):
    return {"method": "cash", "amount": amount}


def test_cash_sale_with_change(client, db, auth, branch, milk, bread):
    response = checkout(
        client,
        auth["cashier"],
        [{"product_id": milk.id, "quantity": 2}, {"product_id": bread.id, "quantity": 3}],
        [cash(20)],
    )
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["receipt_no"] == "DOH-000001"
    assert sale["total"] == 19.0
    assert sale["change_due"] == 1.0
    assert sale["payments"] == [
        {"id": sale["payments"][0]["id"], "method": "cash", "amount": 19.0, "reference": ""}
    ]
    assert sale["item_count"] == 5
    assert sale["cashier_name"] == "Test cashier"

    assert stock_of(db, milk, branch.id) == 18
    assert stock_of(db, bread, branch.id) == 17
    ledger = client.get(
        "/api/inventory/movements",
        params={"product_id": milk.id, "kind": "sale"},
        headers=auth["manager"],
    ).json()
    assert ledger["items"][0]["reference_type"] == "sale"
    assert ledger["items"][0]["reference_id"] == sale["id"]
    assert ledger["items"][0]["note"] == "DOH-000001"
    assert_ledger_consistent(db)


def test_receipt_numbers_count_up_per_branch(client, auth, milk):
    first = checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)])
    second = checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)])
    assert [first.json()["receipt_no"], second.json()["receipt_no"]] == [
        "DOH-000001",
        "DOH-000002",
    ]


def test_split_card_and_cash(client, auth, milk):
    response = checkout(
        client,
        auth["cashier"],
        [{"product_id": milk.id, "quantity": 10}],
        [{"method": "card", "amount": 50, "reference": "APPROVAL 1234"}, cash(20)],
    )
    sale = response.json()
    assert sale["total"] == 65.0
    assert [(p["method"], p["amount"]) for p in sale["payments"]] == [
        ("card", 50.0),
        ("cash", 15.0),
    ]
    assert sale["change_due"] == 5.0


def test_not_enough_stock_rolls_everything_back(client, db, auth, branch, milk, bread):
    response = checkout(
        client,
        auth["cashier"],
        [{"product_id": bread.id, "quantity": 1}, {"product_id": milk.id, "quantity": 21}],
        [cash(500)],
    )
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_stock"
    assert response.json()["context"]["available"] == 20
    assert stock_of(db, bread, branch.id) == 20
    assert db.scalar(select(func.count(Sale.id))) == 0
    assert_ledger_consistent(db)


def test_negative_stock_when_the_shop_allows_it(client, db, auth, branch, milk):
    client.patch("/api/settings", json={"allow_negative_stock": True}, headers=auth["owner"])
    response = checkout(
        client, auth["cashier"], [{"product_id": milk.id, "quantity": 25}], [cash(200)]
    )
    assert response.status_code == 201
    assert stock_of(db, milk, branch.id) == -5
    assert_ledger_consistent(db)


def test_payment_must_cover_total(client, auth, milk):
    short = checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 2}], [cash(10)])
    assert short.status_code == 422
    over_card = checkout(
        client,
        auth["cashier"],
        [{"product_id": milk.id, "quantity": 2}],
        [{"method": "card", "amount": 20}],
    )
    assert over_card.status_code == 422


def test_cashier_discount_limit(client, auth, milk):
    item = [{"product_id": milk.id, "quantity": 2}]
    small = checkout(
        client, auth["cashier"], item, [cash(20)], discount={"type": "percent", "value": 10}
    )
    assert small.status_code == 201
    assert small.json()["total"] == 11.7

    big = checkout(
        client, auth["cashier"], item, [cash(20)], discount={"type": "percent", "value": 20}
    )
    assert big.status_code == 403
    by_manager = checkout(
        client, auth["manager"], item, [cash(20)], discount={"type": "amount", "value": "3.00"}
    )
    assert by_manager.status_code == 201
    assert by_manager.json()["total"] == 10.0


def test_line_discount_by_percent(client, auth, milk, bread):
    response = checkout(
        client,
        auth["manager"],
        [
            {"product_id": milk.id, "quantity": 4, "discount_percent": 25},
            {"product_id": bread.id, "quantity": 1},
        ],
        [cash(50)],
    )
    sale = response.json()
    assert sale["items"][0]["line_discount"] == 6.5
    assert sale["total"] == 21.5


def test_tax_uses_shop_default_and_product_override(client, db, auth, users, branch):
    client.patch("/api/settings", json={"default_tax_rate": 5}, headers=auth["owner"])
    taxed = make_product(db, sale_price="100.00")
    exempt = make_product(db, sale_price="10.00", tax_rate="0")
    give_stock(db, taxed, branch.id, 5, users["manager"])
    give_stock(db, exempt, branch.id, 5, users["manager"])

    sale = checkout(
        client,
        auth["cashier"],
        [{"product_id": taxed.id, "quantity": 1}, {"product_id": exempt.id, "quantity": 1}],
        [{"method": "card", "amount": 115}],
    ).json()
    assert sale["tax_total"] == 5.0
    assert sale["total"] == 115.0
    assert [item["tax_rate"] for item in sale["items"]] == [5.0, 0.0]


def test_inactive_products_cannot_be_sold(client, auth, milk):
    client.patch(f"/api/products/{milk.id}", json={"is_active": False}, headers=auth["manager"])
    response = checkout(
        client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)]
    )
    assert response.status_code == 409


def test_cashier_sells_only_in_own_branch(client, db, auth, milk):
    other = Branch(code="WAK", name="Al Wakra")
    db.add(other)
    db.commit()
    response = checkout(
        client,
        auth["cashier"],
        [{"product_id": milk.id, "quantity": 1}],
        [cash(10)],
        branch_id=other.id,
    )
    assert response.status_code == 403


def test_cashiers_only_see_their_own_sales(client, db, auth, users, milk):
    colleague = User(
        username="cashier2",
        full_name="Second cashier",
        password_hash=hash_password("password123"),
        role=Role.cashier,
        branch_id=users["cashier"].branch_id,
    )
    db.add(colleague)
    db.commit()

    mine = checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)])
    theirs = checkout(
        client, bearer(colleague), [{"product_id": milk.id, "quantity": 1}], [cash(10)]
    )

    own_list = client.get("/api/sales", headers=auth["cashier"]).json()
    assert [s["id"] for s in own_list["items"]] == [mine.json()["id"]]
    assert (
        client.get(f"/api/sales/{theirs.json()['id']}", headers=auth["cashier"]).status_code == 404
    )

    everything = client.get("/api/sales", headers=auth["manager"]).json()
    assert everything["total"] == 2


def test_sale_list_filters(client, auth, milk):
    checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)])
    checkout(client, auth["cashier"], [{"product_id": milk.id, "quantity": 1}], [cash(10)])
    by_receipt = client.get("/api/sales", params={"q": "000002"}, headers=auth["manager"]).json()
    assert [s["receipt_no"] for s in by_receipt["items"]] == ["DOH-000002"]
    old = client.get("/api/sales", params={"date_to": "2020-01-01"}, headers=auth["manager"]).json()
    assert old["total"] == 0


def test_text_receipt(client, auth, milk):
    client.patch("/api/settings", json={"shop_name": "Al Noor Mart"}, headers=auth["owner"])
    sale = checkout(
        client, auth["cashier"], [{"product_id": milk.id, "quantity": 2}], [cash(20)]
    ).json()
    response = client.get(f"/api/sales/{sale['id']}/receipt", headers=auth["cashier"])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    assert "Al Noor Mart" in text
    assert "DOH-000001" in text
    assert "TOTAL QAR" in text
    assert "Change" in text
    assert all(len(line) <= 42 for line in text.splitlines())


def test_business_date_follows_qatar_time(db, users, branch, milk):
    # 22:30 UTC on 30 October is already 01:30 on 31 October in Doha.
    late = datetime(2026, 10, 30, 22, 30, tzinfo=UTC)
    sale = sales.checkout(
        db,
        user=users["cashier"],
        branch_id=branch.id,
        lines=[sales.CartLine(milk.id, 1)],
        payments=[pricing.PaymentInput(PaymentMethod.cash, Decimal("6.50"))],
        at=late,
    )
    db.commit()
    assert sale.business_date == date(2026, 10, 31)


def test_cashier_limit_survives_rounding(client, db, auth, users, branch):
    # 10% of 2.25 is 0.225, which rounds up to 0.23. That is still a 10% discount.
    item = make_product(db, sale_price="2.25")
    give_stock(db, item, branch.id, 5, users["manager"])
    response = checkout(
        client,
        auth["cashier"],
        [{"product_id": item.id, "quantity": 1}],
        [cash(5)],
        discount={"type": "percent", "value": 10},
    )
    assert response.status_code == 201
    assert response.json()["discount_total"] == 0.23
