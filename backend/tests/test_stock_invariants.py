"""Stock consistency invariants.

Random sequences of stock operations are run through the API. Whatever
happens, three things must stay true:

1. every stock level equals the sum of its ledger movements,
2. each movement's balance_after is the running total up to that movement,
3. stock never goes below zero (negative stock is off by default),

the final quantities must match a simple model kept by the test, and the
money on every sale (lines, payments, refunds) must add up.
"""

import random

import pytest

from tests.helpers import (
    assert_ledger_consistent,
    assert_money_consistent,
    make_product,
    stock_of,
)


class Shop:
    """Drives the API and keeps the quantities we expect to see."""

    def __init__(self, client, db, auth, branch_id, rng):
        self.client = client
        self.db = db
        self.auth = auth
        self.branch_id = branch_id
        self.rng = rng
        self.products = [make_product(self.db, name=f"Item {i}") for i in range(4)]
        self.expected = {p.id: 0 for p in self.products}
        self.supplier_id = self.post("/api/suppliers", {"name": "Supplier"}).json()["id"]
        self.sales = []

    def post(self, url, payload=None):
        return self.client.post(url, json=payload, headers=self.auth["manager"])

    def adjust(self, product, **change):
        response = self.client.post(
            "/api/inventory/adjustments",
            json={"product_id": product.id, "reason": "count_correction", **change},
            headers=self.auth["manager"],
        )
        if response.status_code == 201:
            self.expected[product.id] = response.json()["balance_after"]
        else:
            assert response.status_code in (409, 422), response.text
        return response

    def purchase(self, product):
        ordered = self.rng.randint(1, 24)
        po = self.post(
            "/api/purchase-orders",
            {
                "supplier_id": self.supplier_id,
                "items": [{"product_id": product.id, "quantity": ordered}],
            },
        ).json()
        item_id = po["items"][0]["id"]
        delivered = 0
        while delivered < ordered and self.rng.random() < 0.8:
            quantity = self.rng.randint(1, ordered - delivered)
            response = self.post(
                f"/api/purchase-orders/{po['id']}/receive",
                {"lines": [{"item_id": item_id, "quantity": quantity}]},
            )
            assert response.status_code == 200, response.text
            delivered += quantity
            self.expected[product.id] += quantity

    def sell(self):
        basket = self.rng.sample(self.products, self.rng.randint(1, 3))
        items = [{"product_id": p.id, "quantity": self.rng.randint(1, 6)} for p in basket]
        response = self.client.post(
            "/api/sales",
            json={"items": items, "payments": [{"method": "cash", "amount": 1000}]},
            headers=self.auth["cashier"],
        )
        if response.status_code == 201:
            self.sales.append(response.json()["id"])
            for item in items:
                self.expected[item["product_id"]] -= item["quantity"]
        else:
            # Refused sales must not move any stock at all.
            assert response.status_code == 409, response.text
            assert any(self.expected[i["product_id"]] < i["quantity"] for i in items)

    def give_back(self):
        if not self.sales:
            return
        sale_id = self.rng.choice(self.sales)
        sale = self.client.get(f"/api/sales/{sale_id}", headers=self.auth["manager"]).json()
        open_lines = [i for i in sale["items"] if i["quantity"] > i["quantity_returned"]]
        if not open_lines:
            return
        line = self.rng.choice(open_lines)
        quantity = self.rng.randint(1, line["quantity"] - line["quantity_returned"])
        restock = self.rng.random() < 0.8
        response = self.post(
            f"/api/sales/{sale_id}/returns",
            {"items": [{"sale_item_id": line["id"], "quantity": quantity, "restock": restock}]},
        )
        assert response.status_code == 201, response.text
        if restock:
            self.expected[line["product_id"]] += quantity

    def step(self):
        product = self.rng.choice(self.products)
        operation = self.rng.choice(
            ["purchase", "found", "remove", "count", "sell", "sell", "return"]
        )
        if operation == "sell":
            self.sell()
        elif operation == "return":
            self.give_back()
        elif operation == "purchase":
            self.purchase(product)
        elif operation == "found":
            self.adjust(product, quantity_change=self.rng.randint(1, 20))
        elif operation == "remove":
            before = self.expected[product.id]
            response = self.adjust(product, quantity_change=-self.rng.randint(1, 15))
            if response.status_code == 409:
                assert self.expected[product.id] == before
        else:
            self.adjust(product, counted_quantity=self.rng.randint(0, 30))


@pytest.mark.parametrize("seed", range(6))
def test_random_operations_keep_stock_consistent(seed, client, db, auth, branch):
    shop = Shop(client, db, auth, branch.id, random.Random(seed))
    for _ in range(100):
        shop.step()

    assert_ledger_consistent(db)
    assert_money_consistent(db)
    for product in shop.products:
        quantity = stock_of(db, product, branch.id)
        assert quantity >= 0
        assert quantity == shop.expected[product.id]
