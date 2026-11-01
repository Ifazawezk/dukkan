"""Command line helpers.

python -m app.cli create-owner --username owner
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User
from app.security import hash_password


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Dukkan admin commands")
    commands = parser.add_subparsers(dest="command", required=True)

    owner = commands.add_parser("create-owner", help="create the first owner account")
    owner.add_argument("--username", required=True)
    owner.add_argument("--full-name", default="Shop Owner")
    owner.add_argument("--password", help="prompted for when left out")

    args = parser.parse_args(argv)
    if args.command == "create-owner":
        return create_owner(args.username, args.full_name, args.password)
    return 1


if __name__ == "__main__":
    sys.exit(main())
