from datetime import UTC, datetime

from sqlalchemy import func, select

from app import cli
from app.models import Product, PurchaseOrder, PurchaseOrderStatus, Sale, User
from app.seed import DEMO_PASSWORD, clear_database, ean13, seed_demo
from tests.helpers import assert_ledger_consistent, assert_money_consistent

NOW = datetime(2026, 10, 30, 18, 0, tzinfo=UTC)


def test_demo_shop_is_consistent(db, client):
    result = seed_demo(db, days=4, now=NOW)
    assert result.sales > 50
    assert result.products == db.scalar(select(func.count(Product.id)))

    assert_ledger_consistent(db)
    assert_money_consistent(db)

    # Nothing is dated in the future.
    latest = db.scalar(select(func.max(Sale.created_at)))
    assert latest <= NOW

    statuses = set(db.scalars(select(PurchaseOrder.status)))
    assert PurchaseOrderStatus.received in statuses
    assert PurchaseOrderStatus.draft in statuses

    login = client.post("/api/auth/login", data={"username": "rahul", "password": DEMO_PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "cashier"


def test_seed_is_repeatable(db):
    first = seed_demo(db, days=2, now=NOW)
    totals = db.scalar(select(func.sum(Sale.total)))
    clear_database(db)
    assert db.scalar(select(func.count(User.id))) == 0
    second = seed_demo(db, days=2, now=NOW)
    assert (first.sales, first.returns) == (second.sales, second.returns)
    assert db.scalar(select(func.sum(Sale.total))) == totals


def test_seed_command_refuses_to_overwrite(monkeypatch, session_factory, db, users):
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    assert cli.main(["seed", "--days", "1"]) == 1


def test_barcodes_have_valid_check_digits():
    assert ean13("629104150021") == "6291041500213"
    assert ean13("200000000001") == "2000000000015"
