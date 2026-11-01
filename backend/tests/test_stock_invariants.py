"""Stock consistency invariants.

Random sequences of stock operations are run through the API. Whatever
happens, three things must stay true:

1. every stock level equals the sum of its ledger movements,
2. each movement's balance_after is the running total up to that movement,
3. stock never goes below zero (negative stock is off by default),

and the final quantities must match a simple model kept by the test.
"""

import random

import pytest

from tests.helpers import assert_ledger_consistent, make_product, stock_of


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

    def step(self):
        product = self.rng.choice(self.products)
        operation = self.rng.choice(["receive", "remove", "count"])
        if operation == "receive":
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
    for _ in range(80):
        shop.step()

    assert_ledger_consistent(db)
    for product in shop.products:
        quantity = stock_of(db, product, branch.id)
        assert quantity >= 0
        assert quantity == shop.expected[product.id]
