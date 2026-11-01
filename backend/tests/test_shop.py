def test_default_settings_suit_qatar(client, auth):
    response = client.get("/api/settings", headers=auth["cashier"])
    assert response.status_code == 200
    settings = response.json()
    assert settings["currency"] == "QAR"
    assert settings["timezone"] == "Asia/Qatar"
    assert settings["default_tax_rate"] == 0
    assert settings["allow_negative_stock"] is False


def test_owner_updates_settings(client, auth):
    response = client.patch(
        "/api/settings",
        json={"shop_name": "Al Noor Mart", "default_tax_rate": 5, "timezone": "Asia/Dubai"},
        headers=auth["owner"],
    )
    assert response.status_code == 200
    assert response.json()["default_tax_rate"] == 5
    settings = client.get("/api/settings", headers=auth["cashier"]).json()
    assert settings["shop_name"] == "Al Noor Mart"


def test_settings_validation_and_permissions(client, auth):
    forbidden = client.patch("/api/settings", json={"shop_name": "X"}, headers=auth["manager"])
    assert forbidden.status_code == 403
    bad_zone = client.patch("/api/settings", json={"timezone": "Mars/Base"}, headers=auth["owner"])
    assert bad_zone.status_code == 422
    bad_rate = client.patch("/api/settings", json={"default_tax_rate": 120}, headers=auth["owner"])
    assert bad_rate.status_code == 422


def test_branches(client, auth):
    created = client.post(
        "/api/branches",
        json={"code": "WAK", "name": "Al Wakra", "name_ar": "الوكرة"},
        headers=auth["owner"],
    )
    assert created.status_code == 201
    branch_id = created.json()["id"]

    duplicate = client.post(
        "/api/branches", json={"code": "WAK", "name": "Again"}, headers=auth["owner"]
    )
    assert duplicate.status_code == 409
    lower = client.post("/api/branches", json={"code": "wak", "name": "Bad"}, headers=auth["owner"])
    assert lower.status_code == 422

    updated = client.patch(
        f"/api/branches/{branch_id}", json={"phone": "+974 4000 1002"}, headers=auth["owner"]
    )
    assert updated.json()["phone"] == "+974 4000 1002"

    listed = client.get("/api/branches", headers=auth["cashier"]).json()
    assert [b["code"] for b in listed] == ["DOH", "WAK"]


def test_cashier_cannot_create_branch(client, auth):
    response = client.post(
        "/api/branches", json={"code": "X1", "name": "X"}, headers=auth["cashier"]
    )
    assert response.status_code == 403
