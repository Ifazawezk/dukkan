from datetime import timedelta

import jwt

from app.db_types import utcnow
from tests.conftest import PASSWORD


def login(client, username, password=PASSWORD):
    return client.post("/api/auth/login", data={"username": username, "password": password})


def test_login_returns_token_that_works(client, users):
    response = login(client, "cashier")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "cashier"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "cashier"
    assert me.json()["last_login_at"] is not None


def test_username_is_case_insensitive(client, users):
    assert login(client, "  Manager ").status_code == 200


def test_wrong_password_and_unknown_user_are_rejected(client, users):
    assert login(client, "owner", "wrong-password").status_code == 401
    assert login(client, "nobody").status_code == 401


def test_inactive_user_cannot_log_in(client, db, users):
    users["cashier"].is_active = False
    db.commit()
    assert login(client, "cashier").status_code == 401


def test_protected_endpoint_requires_valid_token(client, users):
    assert client.get("/api/auth/me").status_code == 401
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401


def test_expired_token_is_rejected(client, users):
    expired = jwt.encode(
        {"sub": str(users["owner"].id), "exp": utcnow() - timedelta(minutes=1)},
        "test-secret-key-that-is-long-enough-for-hs256",
        algorithm="HS256",
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_of_deactivated_user_stops_working(client, db, users, auth):
    users["manager"].is_active = False
    db.commit()
    assert client.get("/api/auth/me", headers=auth["manager"]).status_code == 401


def test_change_password(client, users, auth):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "a-new-password"},
        headers=auth["cashier"],
    )
    assert response.status_code == 204
    assert login(client, "cashier").status_code == 401
    assert login(client, "cashier", "a-new-password").status_code == 200


def test_change_password_needs_current_password(client, users, auth):
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "nope", "new_password": "a-new-password"},
        headers=auth["cashier"],
    )
    assert response.status_code == 400
