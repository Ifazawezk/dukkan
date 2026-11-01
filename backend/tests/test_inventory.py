import pytest
from sqlalchemy import update

from app.models import Branch, StockLevel
from tests.helpers import assert_ledger_consistent, give_stock, make_product, stock_of


@pytest.fixture
def other_branch(db):
    branch = Branch(code="WAK", name="Al Wakra")
    db.add(branch)
    db.commit()
    return branch


def adjust(client, headers, **payload):
    payload.setdefault("reason", "opening_stock")
    return client.post("/api/inventory/adjustments", json=payload, headers=headers)


def test_adjustment_adds_stock_and_writes_ledger(client, db, auth, branch):
    product = make_product(db)
    response = adjust(client, auth["manager"], product_id=product.id, quantity_change=24)
    assert response.status_code == 201
    movement = response.json()
    assert movement["kind"] == "adjustment"
    assert movement["reason"] == "opening_stock"
    assert movement["balance_after"] == 24
    assert movement["branch_id"] == branch.id  # manager's home branch
    assert movement["user_name"] == "Test manager"
    assert stock_of(db, product, branch.id) == 24


def test_counted_quantity_sets_stock(client, db, auth, users, branch):
    product = make_product(db)
    give_stock(db, product, branch.id, 10, users["manager"])
    response = adjust(
        client,
        auth["manager"],
        product_id=product.id,
        counted_quantity=7,
        reason="count_correction",
    )
    assert response.status_code == 201
    assert response.json()["quantity_change"] == -3
    assert stock_of(db, product, branch.id) == 7

    same = adjust(client, auth["manager"], product_id=product.id, counted_quantity=7)
    assert same.status_code == 422


def test_cannot_remove_more_than_on_hand(client, db, auth, users, branch):
    product = make_product(db)
    give_stock(db, product, branch.id, 2, users["manager"])
    response = adjust(
        client, auth["manager"], product_id=product.id, quantity_change=-5, reason="damaged"
    )
    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_stock"
    assert response.json()["context"]["available"] == 2
    assert stock_of(db, product, branch.id) == 2
    assert_ledger_consistent(db)


def test_adjustment_payload_validation(client, db, auth):
    product = make_product(db)
    both = adjust(
        client, auth["manager"], product_id=product.id, quantity_change=1, counted_quantity=1
    )
    assert both.status_code == 422
    neither = adjust(client, auth["manager"], product_id=product.id)
    assert neither.status_code == 422
    zero = adjust(client, auth["manager"], product_id=product.id, quantity_change=0)
    assert zero.status_code == 422
    bad_reason = adjust(
        client, auth["manager"], product_id=product.id, quantity_change=1, reason="x"
    )
    assert bad_reason.status_code == 422


def test_cashier_cannot_adjust(client, db, auth):
    product = make_product(db)
    response = adjust(client, auth["cashier"], product_id=product.id, quantity_change=5)
    assert response.status_code == 403


def test_stock_list_with_low_stock_filter(client, db, auth, users, branch):
    plenty = make_product(db, name="Plenty", threshold=5)
    low = make_product(db, name="Low", threshold=5)
    make_product(db, name="Never stocked", threshold=5)
    give_stock(db, plenty, branch.id, 50, users["manager"])
    give_stock(db, low, branch.id, 3, users["manager"])

    everything = client.get("/api/inventory/stock", headers=auth["manager"]).json()
    by_name = {row["name"]: row for row in everything["items"]}
    assert by_name["Plenty"]["quantity"] == 50
    assert by_name["Plenty"]["stock_value"] == 300.0  # 50 x 6.00 cost
    assert by_name["Never stocked"]["quantity"] == 0

    low_only = client.get(
        "/api/inventory/stock", params={"low_only": True}, headers=auth["manager"]
    ).json()
    assert sorted(row["name"] for row in low_only["items"]) == ["Low", "Never stocked"]
    assert all(row["is_low"] for row in low_only["items"])


def test_cashier_sees_own_branch_without_costs(client, db, auth, other_branch):
    make_product(db)
    own = client.get("/api/inventory/stock", headers=auth["cashier"])
    assert own.status_code == 200
    assert own.json()["items"][0]["cost_price"] is None
    other = client.get(
        "/api/inventory/stock", params={"branch_id": other_branch.id}, headers=auth["cashier"]
    )
    assert other.status_code == 403


def test_stock_is_kept_per_branch(client, db, auth, users, branch, other_branch):
    product = make_product(db)
    give_stock(db, product, branch.id, 10, users["manager"])
    give_stock(db, product, other_branch.id, 4, users["manager"])

    rows = client.get(f"/api/inventory/stock/{product.id}/branches", headers=auth["cashier"]).json()
    assert [(r["branch_code"], r["quantity"]) for r in rows] == [("DOH", 10), ("WAK", 4)]

    listing = client.get(
        "/api/products", params={"branch_id": other_branch.id}, headers=auth["manager"]
    ).json()
    assert listing["items"][0]["stock"] == 4
    lookup = client.get(
        "/api/products/lookup", params={"code": product.sku}, headers=auth["cashier"]
    ).json()
    assert lookup["stock"] == 10


def test_movement_history_filters(client, db, auth, users, branch):
    first = make_product(db)
    second = make_product(db)
    give_stock(db, first, branch.id, 5, users["manager"])
    give_stock(db, second, branch.id, 8, users["manager"])
    give_stock(db, first, branch.id, 2, users["manager"])

    history = client.get(
        "/api/inventory/movements", params={"product_id": first.id}, headers=auth["manager"]
    ).json()
    assert history["total"] == 2
    assert [m["balance_after"] for m in history["items"]] == [7, 5]  # newest first

    assert client.get("/api/inventory/movements", headers=auth["cashier"]).status_code == 403


def test_verify_detects_tampering(client, db, auth, users, branch):
    product = make_product(db)
    give_stock(db, product, branch.id, 5, users["manager"])
    clean = client.get("/api/inventory/verify", headers=auth["manager"]).json()
    assert clean == {"ok": True, "pairs_checked": 1, "problems": []}

    # Someone edits the stock table by hand, bypassing the ledger.
    db.execute(update(StockLevel).values(quantity=99))
    db.commit()
    broken = client.get("/api/inventory/verify", headers=auth["manager"]).json()
    assert broken["ok"] is False
    assert broken["problems"][0]["stock_level"] == 99
    assert broken["problems"][0]["ledger_total"] == 5
