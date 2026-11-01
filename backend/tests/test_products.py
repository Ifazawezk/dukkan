import pytest


@pytest.fixture
def drinks(client, auth):
    response = client.post(
        "/api/categories", json={"name": "Beverages", "name_ar": "مشروبات"}, headers=auth["manager"]
    )
    assert response.status_code == 201
    return response.json()


def make_product(client, headers, **overrides):
    payload = {
        "sku": "BEV-001",
        "barcode": "2000000000015",
        "name": "Mineral Water 500ml",
        "name_ar": "مياه معدنية ٥٠٠ مل",
        "cost_price": "0.55",
        "sale_price": "1.00",
    }
    payload.update(overrides)
    return client.post("/api/products", json=payload, headers=headers)


def test_manager_creates_product(client, auth, drinks):
    response = make_product(client, auth["manager"], category_id=drinks["id"])
    assert response.status_code == 201
    product = response.json()
    assert product["sku"] == "BEV-001"
    assert product["sale_price"] == 1.0
    assert product["cost_price"] == 0.55
    assert product["tax_rate"] is None
    assert product["low_stock_threshold"] == 5  # shop default


def test_sku_is_normalised_to_upper_case(client, auth):
    response = make_product(client, auth["manager"], sku=" bev-009 ")
    assert response.json()["sku"] == "BEV-009"


def test_cashier_reads_but_cannot_write(client, auth):
    assert make_product(client, auth["cashier"]).status_code == 403
    make_product(client, auth["manager"])
    listing = client.get("/api/products", headers=auth["cashier"])
    assert listing.status_code == 200
    # Cost prices are a manager concern.
    assert listing.json()["items"][0]["cost_price"] is None


def test_duplicate_sku_or_barcode_conflicts(client, auth):
    make_product(client, auth["manager"])
    same_sku = make_product(client, auth["manager"], barcode="2000000000022")
    assert same_sku.status_code == 409
    same_barcode = make_product(client, auth["manager"], sku="BEV-002")
    assert same_barcode.status_code == 409


def test_amounts_are_validated(client, auth):
    assert make_product(client, auth["manager"], sale_price="1.005").status_code == 422
    assert make_product(client, auth["manager"], sale_price=-1).status_code == 422
    assert make_product(client, auth["manager"], tax_rate=101).status_code == 422


def test_unknown_category_is_rejected(client, auth):
    assert make_product(client, auth["manager"], category_id=99).status_code == 404


def test_search_in_english_arabic_sku_and_barcode(client, auth):
    make_product(client, auth["manager"])
    make_product(
        client,
        auth["manager"],
        sku="DAI-001",
        barcode="2000000000039",
        name="Fresh Milk 1L",
        name_ar="حليب طازج ١ لتر",
        sale_price="6.50",
    )

    def search(q):
        response = client.get("/api/products", params={"q": q}, headers=auth["cashier"])
        return [p["sku"] for p in response.json()["items"]]

    assert search("milk") == ["DAI-001"]
    assert search("حليب") == ["DAI-001"]
    assert search("bev") == ["BEV-001"]
    assert search("0000039") == ["DAI-001"]
    assert search("%") == []  # wildcards are matched literally


def test_lookup_by_barcode_or_sku(client, auth):
    make_product(client, auth["manager"])
    by_barcode = client.get(
        "/api/products/lookup", params={"code": "2000000000015"}, headers=auth["cashier"]
    )
    assert by_barcode.json()["sku"] == "BEV-001"
    by_sku = client.get("/api/products/lookup", params={"code": "bev-001"}, headers=auth["cashier"])
    assert by_sku.json()["sku"] == "BEV-001"
    missing = client.get("/api/products/lookup", params={"code": "123"}, headers=auth["cashier"])
    assert missing.status_code == 404


def test_update_and_deactivate(client, auth):
    product_id = make_product(client, auth["manager"]).json()["id"]
    response = client.patch(
        f"/api/products/{product_id}",
        json={"sale_price": "1.25", "barcode": None, "is_active": False},
        headers=auth["manager"],
    )
    assert response.status_code == 200
    assert response.json()["sale_price"] == 1.25
    assert response.json()["barcode"] is None

    active = client.get("/api/products", headers=auth["manager"]).json()
    assert active["total"] == 0
    everything = client.get(
        "/api/products", params={"include_inactive": True}, headers=auth["manager"]
    ).json()
    assert everything["total"] == 1


def test_update_cannot_steal_another_sku(client, auth):
    make_product(client, auth["manager"])
    other = make_product(client, auth["manager"], sku="BEV-002", barcode=None).json()
    response = client.patch(
        f"/api/products/{other['id']}", json={"sku": "BEV-001"}, headers=auth["manager"]
    )
    assert response.status_code == 409


def test_pagination(client, auth):
    for i in range(5):
        make_product(client, auth["manager"], sku=f"P-{i}", barcode=None, name=f"Item {i}")
    page = client.get(
        "/api/products", params={"limit": 2, "offset": 2}, headers=auth["manager"]
    ).json()
    assert page["total"] == 5
    assert [p["name"] for p in page["items"]] == ["Item 2", "Item 3"]


def test_categories_count_products_and_block_delete(client, auth, drinks):
    make_product(client, auth["manager"], category_id=drinks["id"])
    listed = client.get("/api/categories", headers=auth["cashier"]).json()
    assert listed[0]["product_count"] == 1

    blocked = client.delete(f"/api/categories/{drinks['id']}", headers=auth["manager"])
    assert blocked.status_code == 409

    empty = client.post("/api/categories", json={"name": "Bakery"}, headers=auth["manager"]).json()
    assert (
        client.delete(f"/api/categories/{empty['id']}", headers=auth["manager"]).status_code == 204
    )


def test_category_names_are_unique_ignoring_case(client, auth, drinks):
    response = client.post("/api/categories", json={"name": "beverages"}, headers=auth["manager"])
    assert response.status_code == 409
