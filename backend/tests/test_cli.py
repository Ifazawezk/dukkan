from sqlalchemy import select, update

from app import cli
from app.models import Role, StockLevel, User
from app.security import verify_password
from tests.helpers import give_stock, make_product


def test_create_owner(monkeypatch, session_factory, db):
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    assert cli.main(["create-owner", "--username", "Boss", "--password", "long-enough"]) == 0

    owner = db.scalar(select(User).where(User.username == "boss"))
    assert owner.role == Role.owner
    assert verify_password("long-enough", owner.password_hash)

    # A second run with the same name refuses instead of overwriting.
    assert cli.main(["create-owner", "--username", "boss", "--password", "long-enough"]) == 1


def test_create_owner_rejects_short_password(monkeypatch, session_factory):
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    assert cli.main(["create-owner", "--username", "boss", "--password", "short"]) == 1


def test_verify_stock(monkeypatch, session_factory, db, users, branch, capsys):
    monkeypatch.setattr(cli, "SessionLocal", session_factory)
    give_stock(db, make_product(db), branch.id, 3, users["manager"])
    assert cli.main(["verify-stock"]) == 0
    assert "0 problem(s)" in capsys.readouterr().out

    db.execute(update(StockLevel).values(quantity=1))
    db.commit()
    assert cli.main(["verify-stock"]) == 1
