import pytest

from tests.helpers import assert_ledger_consistent, give_stock, make_product, stock_of


@pytest.fixture
def stocked(db, users, branch):
    """Two products with 50 units each in the test branch."""
    items = []
    for name, price in [("Dates 1kg", "10.00"), ("Arabic Coffee 250g", "3.33")]:
        product = make_product(db, name=name, sale_price=price, cost_price="2.00")
        give_stock(db, product, branch.id, 50, users["manager"])
        items.append(product)
    return items


def sell(client, auth, items, payments=None, discount=None):
    payload = {
        "items": items,
        "payments": payments or [{"method": "cash", "amount": 1000}],
        "discount": discount,
    }
    response = client.post("/api/sales", json=payload, headers=auth["manager"])
    assert response.status_code == 201, response.text
    return response.json()


def give_back(client, auth, sale, lines, **extra):
    return client.post(
        f"/api/sales/{sale['id']}/returns",
        json={"items": lines, **extra},
        headers=auth["manager"],
    )


def test_return_refunds_and_restocks(client, db, auth, branch, stocked):
    dates, coffee = stocked
    sale = sell(
        client,
        auth,
        [{"product_id": dates.id, "quantity": 2}, {"product_id": coffee.id, "quantity": 1}],
    )
    line = sale["items"][0]
    response = give_back(
        client, auth, sale, [{"sale_item_id": line["id"], "quantity": 2}], reason="Wrong size"
    )
    assert response.status_code == 201, response.text
    refund = response.json()
    assert refund["return_no"] == "DOH-R00001"
    assert refund["refund_total"] == 20.0
    assert refund["refund_method"] == "cash"
    assert refund["items"][0]["restocked"] is True
    assert stock_of(db, dates, branch.id) == 50

    detail = client.get(f"/api/sales/{sale['id']}", headers=auth["manager"]).json()
    assert detail["status"] == "partially_refunded"
    assert detail["refunded_total"] == 20.0
    assert detail["items"][0]["quantity_returned"] == 2
    assert [r["return_no"] for r in detail["returns"]] == ["DOH-R00001"]

    ledger = client.get(
        "/api/inventory/movements",
        params={"product_id": dates.id, "kind": "return"},
        headers=auth["manager"],
    ).json()
    assert ledger["items"][0]["quantity_change"] == 2
    assert ledger["items"][0]["reference_type"] == "sale_return"
    assert_ledger_consistent(db)


def test_refund_respects_discount_and_adds_up_exactly(client, auth, stocked):
    _, coffee = stocked
    # 3 x 3.33 = 9.99, less 10% = 8.99 paid for the line.
    sale = sell(
        client,
        auth,
        [{"product_id": coffee.id, "quantity": 3}],
        discount={"type": "percent", "value": 10},
    )
    line = sale["items"][0]
    assert line["line_total"] == 8.99

    refunds = []
    for _ in range(3):
        response = give_back(client, auth, sale, [{"sale_item_id": line["id"], "quantity": 1}])
        refunds.append(response.json()["refund_total"])
    assert refunds == [3.0, 3.0, 2.99]
    assert round(sum(refunds), 2) == 8.99

    detail = client.get(f"/api/sales/{sale['id']}", headers=auth["manager"]).json()
    assert detail["status"] == "refunded"
    assert detail["refunded_total"] == 8.99


def test_cannot_return_more_than_sold(client, auth, stocked):
    dates, _ = stocked
    sale = sell(client, auth, [{"product_id": dates.id, "quantity": 2}])
    line_id = sale["items"][0]["id"]
    give_back(client, auth, sale, [{"sale_item_id": line_id, "quantity": 1}])
    response = give_back(client, auth, sale, [{"sale_item_id": line_id, "quantity": 2}])
    assert response.status_code == 422
    assert response.json()["context"]["returnable"] == 1

    unknown = give_back(client, auth, sale, [{"sale_item_id": 9999, "quantity": 1}])
    assert unknown.status_code == 404


def test_damaged_goods_are_refunded_but_not_restocked(client, db, auth, branch, stocked):
    dates, _ = stocked
    sale = sell(client, auth, [{"product_id": dates.id, "quantity": 1}])
    response = give_back(
        client,
        auth,
        sale,
        [{"sale_item_id": sale["items"][0]["id"], "quantity": 1, "restock": False}],
        reason="Packet torn",
    )
    assert response.json()["items"][0]["restocked"] is False
    assert stock_of(db, dates, branch.id) == 49
    assert_ledger_consistent(db)


def test_refund_method_defaults_to_how_customer_paid(client, auth, stocked):
    dates, _ = stocked
    sale = sell(
        client, auth, [{"product_id": dates.id, "quantity": 1}], [{"method": "card", "amount": 10}]
    )
    line = {"sale_item_id": sale["items"][0]["id"], "quantity": 1}
    assert give_back(client, auth, sale, [line]).json()["refund_method"] == "card"


def test_only_managers_take_returns(client, auth, stocked):
    dates, _ = stocked
    sale = sell(client, auth, [{"product_id": dates.id, "quantity": 1}])
    response = client.post(
        f"/api/sales/{sale['id']}/returns",
        json={"items": [{"sale_item_id": sale["items"][0]["id"], "quantity": 1}]},
        headers=auth["cashier"],
    )
    assert response.status_code == 403


def test_returns_list(client, auth, stocked):
    dates, coffee = stocked
    first = sell(client, auth, [{"product_id": dates.id, "quantity": 1}])
    second = sell(client, auth, [{"product_id": coffee.id, "quantity": 1}])
    give_back(client, auth, first, [{"sale_item_id": first["items"][0]["id"], "quantity": 1}])
    give_back(client, auth, second, [{"sale_item_id": second["items"][0]["id"], "quantity": 1}])

    listed = client.get("/api/returns", headers=auth["manager"]).json()
    assert listed["total"] == 2
    assert listed["items"][0]["receipt_no"] == second["receipt_no"]
    assert listed["items"][0]["items"][0]["product_name"] == "Arabic Coffee 250g"
    assert client.get("/api/returns", headers=auth["cashier"]).status_code == 403
