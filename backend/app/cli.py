"""Command line helpers.

python -m app.cli create-owner --username owner
python -m app.cli verify-stock
python -m app.cli seed --reset
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User
from app.security import hash_password
from app.seed import DEMO_PASSWORD, clear_database, database_is_empty, seed_demo
from app.services.inventory import verify_ledger


def create_owner(username: str, full_name: str, password: str | None) -> int:
    username = username.strip().lower()
    if password is None:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.username == username)):
            print(f"User {username!r} already exists.", file=sys.stderr)
            return 1
        db.add(
            User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                role=Role.owner,
            )
        )
        db.commit()
    print(f"Created owner account {username!r}.")
    return 0


def verify_stock() -> int:
    with SessionLocal() as db:
        checked, problems = verify_ledger(db)
    for problem in problems:
        print(
            f"product {problem.product_id} branch {problem.branch_id}: {problem.problem} "
            f"(stock level {problem.stock_level}, ledger {problem.ledger_total})"
        )
    print(f"Checked {checked} product/branch pairs, {len(problems)} problem(s).")
    return 1 if problems else 0


def seed(days: int, reset: bool) -> int:
    with SessionLocal() as db:
        if not database_is_empty(db):
            if not reset:
                print(
                    "The database already has data. Use --reset to wipe it first.",
                    file=sys.stderr,
                )
                return 1
            clear_database(db)
        print(f"Creating the demo shop with {days} days of trading...")
        result = seed_demo(db, days=days)
    print(
        f"Done in {result.seconds:.1f}s: {result.products} products, {result.sales} sales, "
        f"{result.returns} returns, {result.purchase_orders} purchase orders."
    )
    print(f"Log in as owner, manager, rahul, maria or omar with the password {DEMO_PASSWORD!r}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Dukkan admin commands")
    commands = parser.add_subparsers(dest="command", required=True)

    owner = commands.add_parser("create-owner", help="create the first owner account")
    owner.add_argument("--username", required=True)
    owner.add_argument("--full-name", default="Shop Owner")
    owner.add_argument("--password", help="prompted for when left out")

    commands.add_parser("verify-stock", help="check stock levels against the movement ledger")

    demo = commands.add_parser("seed", help="fill the database with a demo shop")
    demo.add_argument("--days", type=int, default=45, help="days of sales history (default 45)")
    demo.add_argument("--reset", action="store_true", help="delete all existing data first")

    args = parser.parse_args(argv)
    if args.command == "create-owner":
        return create_owner(args.username, args.full_name, args.password)
    if args.command == "verify-stock":
        return verify_stock()
    if args.command == "seed":
        return seed(args.days, args.reset)
    return 1


if __name__ == "__main__":
    sys.exit(main())
