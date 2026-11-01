from tests.conftest import PASSWORD


def new_user(**overrides):
    payload = {
        "username": "sara",
        "full_name": "Sara Ahmed",
        "password": "secret-pass",
        "role": "cashier",
    }
    payload.update(overrides)
    return payload


def test_owner_creates_user_who_can_log_in(client, auth, branch):
    response = client.post("/api/users", json=new_user(branch_id=branch.id), headers=auth["owner"])
    assert response.status_code == 201
    assert response.json()["role"] == "cashier"
    assert "password_hash" not in response.json()

    login = client.post("/api/auth/login", data={"username": "sara", "password": "secret-pass"})
    assert login.status_code == 200


def test_only_owner_manages_users(client, auth, branch):
    payload = new_user(branch_id=branch.id)
    assert client.post("/api/users", json=payload, headers=auth["manager"]).status_code == 403
    assert client.get("/api/users", headers=auth["cashier"]).status_code == 403
    assert client.get("/api/users", headers=auth["manager"]).status_code == 200


def test_duplicate_username_conflicts(client, auth, branch):
    response = client.post(
        "/api/users", json=new_user(username="Cashier", branch_id=branch.id), headers=auth["owner"]
    )
    assert response.status_code == 409


def test_cashier_needs_a_branch(client, auth):
    response = client.post("/api/users", json=new_user(), headers=auth["owner"])
    assert response.status_code == 422


def test_validation_of_username_and_password(client, auth, branch):
    bad_name = new_user(username="no spaces allowed", branch_id=branch.id)
    assert client.post("/api/users", json=bad_name, headers=auth["owner"]).status_code == 422
    short = new_user(password="short", branch_id=branch.id)
    assert client.post("/api/users", json=short, headers=auth["owner"]).status_code == 422
    # 40 Arabic letters are 80 bytes in UTF-8, more than bcrypt can take.
    too_long = new_user(password="ش" * 40, branch_id=branch.id)
    assert client.post("/api/users", json=too_long, headers=auth["owner"]).status_code == 422


def test_owner_can_reset_password_and_change_role(client, auth, users):
    cashier_id = users["cashier"].id
    response = client.patch(
        f"/api/users/{cashier_id}",
        json={"role": "manager", "password": "brand-new-pass"},
        headers=auth["owner"],
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"
    old = client.post("/api/auth/login", data={"username": "cashier", "password": PASSWORD})
    assert old.status_code == 401


def test_owner_cannot_lock_themselves_out(client, auth, users):
    owner_id = users["owner"].id
    demote = client.patch(f"/api/users/{owner_id}", json={"role": "cashier"}, headers=auth["owner"])
    assert demote.status_code == 409
    disable = client.patch(
        f"/api/users/{owner_id}", json={"is_active": False}, headers=auth["owner"]
    )
    assert disable.status_code == 409


def test_unknown_user_is_404(client, auth):
    assert client.get("/api/users/999", headers=auth["manager"]).status_code == 404
