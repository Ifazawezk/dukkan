from decimal import Decimal

import pytest

from app.services.purchasing import moving_average_cost
from tests.helpers import assert_ledger_consistent, give_stock, make_product, stock_of


@pytest.fixture
def supplier(client, auth):
    response = client.post(
        "/api/suppliers",
        json={"name": "Gulf Foods Trading", "phone": "+974 4000 2000", "email": "orders@gulf.test"},
        headers=auth["manager"],
    )
    assert response.status_code == 201
    return response.json()


def create_po(client, auth, supplier, items, **extra):
    payload = {"supplier_id": supplier["id"], "items": items, **extra}
    return client.post("/api/purchase-orders", json=payload, headers=auth["manager"])


def receive(client, auth, po, lines):
    return client.post(
        f"/api/purchase-orders/{po['id']}/receive", json={"lines": lines}, headers=auth["manager"]
    )


def test_supplier_management(client, auth, supplier):
    duplicate = client.post(
        "/api/suppliers", json={"name": "gulf foods trading"}, headers=auth["manager"]
    )
    assert duplicate.status_code == 409
    bad_email = client.post(
        "/api/suppliers", json={"name": "X", "email": "not-an-email"}, headers=auth["manager"]
    )
    assert bad_email.status_code == 422
    assert client.get("/api/suppliers", headers=auth["cashier"]).status_code == 403

    client.patch(
        f"/api/suppliers/{supplier['id']}", json={"is_active": False}, headers=auth["manager"]
    )
    assert client.get("/api/suppliers", headers=auth["manager"]).json() == []
    everyone = client.get(
        "/api/suppliers", params={"include_inactive": True}, headers=auth["manager"]
    ).json()
    assert len(everyone) == 1


def test_create_draft_uses_product_cost_by_default(client, db, auth, supplier, branch):
    water = make_product(db, cost_price="0.55")
    milk = make_product(db, cost_price="5.10")
    response = create_po(
        client,
        auth,
        supplier,
        [
            {"product_id": water.id, "quantity": 48},
            {"product_id": milk.id, "quantity": 12, "unit_cost": "5.00"},
        ],
        expected_date="2026-11-02",
    )
    assert response.status_code == 201
    po = response.json()
    assert po["number"] == "PO-00001"
    assert po["status"] == "draft"
    assert po["branch_id"] == branch.id
    assert [item["unit_cost"] for item in po["items"]] == [0.55, 5.0]
    assert po["total_cost"] == 86.4  # 48 x 0.55 + 12 x 5.00

    second = create_po(client, auth, supplier, [{"product_id": water.id, "quantity": 1}])
    assert second.json()["number"] == "PO-00002"


def test_purchase_order_validation(client, db, auth, supplier):
    item = make_product(db)
    twice = create_po(
        client,
        auth,
        supplier,
        [{"product_id": item.id, "quantity": 1}, {"product_id": item.id, "quantity": 2}],
    )
    assert twice.status_code == 422
    assert create_po(client, auth, supplier, []).status_code == 422
    zero = create_po(client, auth, supplier, [{"product_id": item.id, "quantity": 0}])
    assert zero.status_code == 422
    unknown = create_po(client, auth, supplier, [{"product_id": 999, "quantity": 1}])
    assert unknown.status_code == 404
    cashier = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier["id"], "items": [{"product_id": item.id, "quantity": 1}]},
        headers=auth["cashier"],
    )
    assert cashier.status_code == 403


def test_inactive_supplier_cannot_get_new_orders(client, db, auth, supplier):
    client.patch(
        f"/api/suppliers/{supplier['id']}", json={"is_active": False}, headers=auth["manager"]
    )
    response = create_po(
        client, auth, supplier, [{"product_id": make_product(db).id, "quantity": 1}]
    )
    assert response.status_code == 409


def test_draft_can_be_edited_until_submitted(client, db, auth, supplier):
    first, second = make_product(db), make_product(db)
    po = create_po(client, auth, supplier, [{"product_id": first.id, "quantity": 5}]).json()

    edited = client.patch(
        f"/api/purchase-orders/{po['id']}",
        json={"items": [{"product_id": second.id, "quantity": 7}], "notes": "Call before delivery"},
        headers=auth["manager"],
    ).json()
    assert [(i["product_id"], i["quantity_ordered"]) for i in edited["items"]] == [(second.id, 7)]
    assert edited["notes"] == "Call before delivery"

    submitted = client.post(f"/api/purchase-orders/{po['id']}/submit", headers=auth["manager"])
    assert submitted.json()["status"] == "ordered"
    assert submitted.json()["ordered_at"] is not None

    late_edit = client.patch(
        f"/api/purchase-orders/{po['id']}", json={"notes": "too late"}, headers=auth["manager"]
    )
    assert late_edit.status_code == 409


def test_partial_then_full_receipt_updates_stock(client, db, auth, supplier, branch):
    product = make_product(db)
    po = create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 30}]).json()
    item_id = po["items"][0]["id"]

    partial = receive(client, auth, po, [{"item_id": item_id, "quantity": 10}])
    assert partial.status_code == 200
    assert partial.json()["status"] == "partially_received"
    assert stock_of(db, product, branch.id) == 10

    too_many = receive(client, auth, po, [{"item_id": item_id, "quantity": 21}])
    assert too_many.status_code == 422
    assert too_many.json()["context"]["remaining"] == 20

    full = receive(client, auth, po, [{"item_id": item_id, "quantity": 20}])
    assert full.json()["status"] == "received"
    assert full.json()["received_at"] is not None
    assert stock_of(db, product, branch.id) == 30

    again = receive(client, auth, po, [{"item_id": item_id, "quantity": 1}])
    assert again.status_code == 409

    ledger = client.get(
        "/api/inventory/movements",
        params={"product_id": product.id, "kind": "purchase"},
        headers=auth["manager"],
    ).json()
    assert [m["quantity_change"] for m in ledger["items"]] == [20, 10]
    assert ledger["items"][0]["reference_type"] == "purchase_order"
    assert ledger["items"][0]["reference_id"] == po["id"]
    assert_ledger_consistent(db)


def test_receiving_updates_moving_average_cost(client, db, auth, users, supplier, branch):
    product = make_product(db, cost_price="6.00")
    give_stock(db, product, branch.id, 10, users["manager"])
    po = create_po(
        client, auth, supplier, [{"product_id": product.id, "quantity": 10, "unit_cost": "8.00"}]
    ).json()
    receive(client, auth, po, [{"item_id": po["items"][0]["id"], "quantity": 10}])

    updated = client.get(f"/api/products/{product.id}", headers=auth["manager"]).json()
    assert updated["cost_price"] == 7.0


def test_invoice_price_overrides_ordered_price(client, db, auth, supplier):
    product = make_product(db, cost_price="6.00")
    po = create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 4}]).json()
    received = receive(
        client, auth, po, [{"item_id": po["items"][0]["id"], "quantity": 4, "unit_cost": "6.40"}]
    ).json()
    assert received["items"][0]["unit_cost"] == 6.4
    product_now = client.get(f"/api/products/{product.id}", headers=auth["manager"]).json()
    assert product_now["cost_price"] == 6.4  # nothing was on hand before


def test_cancel_rules(client, db, auth, supplier):
    product = make_product(db)
    draft = create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 5}]).json()
    cancelled = client.post(f"/api/purchase-orders/{draft['id']}/cancel", headers=auth["manager"])
    assert cancelled.json()["status"] == "cancelled"
    blocked = receive(client, auth, draft, [{"item_id": draft["items"][0]["id"], "quantity": 1}])
    assert blocked.status_code == 409

    started = create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 5}]).json()
    receive(client, auth, started, [{"item_id": started["items"][0]["id"], "quantity": 2}])
    refused = client.post(f"/api/purchase-orders/{started['id']}/cancel", headers=auth["manager"])
    assert refused.status_code == 409


def test_list_filters_by_status(client, db, auth, supplier):
    product = make_product(db)
    first = create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 1}]).json()
    create_po(client, auth, supplier, [{"product_id": product.id, "quantity": 1}])
    client.post(f"/api/purchase-orders/{first['id']}/submit", headers=auth["manager"])

    ordered = client.get(
        "/api/purchase-orders", params={"status": "ordered"}, headers=auth["manager"]
    ).json()
    assert ordered["total"] == 1
    assert ordered["items"][0]["supplier_name"] == "Gulf Foods Trading"
    everything = client.get("/api/purchase-orders", headers=auth["manager"]).json()
    assert [po["number"] for po in everything["items"]] == ["PO-00002", "PO-00001"]


@pytest.mark.parametrize(
    ("on_hand", "cost", "qty", "unit_cost", "expected"),
    [
        (0, "5.00", 10, "6.00", "6.00"),
        (10, "6.00", 10, "8.00", "7.00"),
        (3, "1.00", 1, "2.00", "1.25"),
        (2, "1.00", 1, "1.01", "1.00"),  # 1.00333 rounds down
        (-4, "9.99", 5, "3.00", "3.00"),  # negative stock counts as none
    ],
)
def test_moving_average_cost(on_hand, cost, qty, unit_cost, expected):
    assert moving_average_cost(on_hand, Decimal(cost), qty, Decimal(unit_cost)) == Decimal(expected)
