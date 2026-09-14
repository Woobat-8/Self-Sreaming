from __future__ import annotations

import argparse
import sys
from getpass import getpass

from app.database import SessionLocal, init_db
from app.services.auth import create_user, set_password


def _password_arg(value: str | None) -> str:
    if value:
        return value
    return getpass("Password: ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Media service admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-admin", help="Create the first (or another) admin user")
    create.add_argument("--username", required=True)
    create.add_argument("--password", default=None)

    reset = sub.add_parser("reset-password", help="Set a user's password")
    reset.add_argument("--username", required=True)
    reset.add_argument("--password", default=None)

    args = parser.parse_args(argv)
    init_db()
    db = SessionLocal()
    try:
        if args.command == "create-admin":
            create_user(db, args.username, _password_arg(args.password), role="admin")
            print(f"Created admin user {args.username}")
        elif args.command == "reset-password":
            set_password(db, args.username, _password_arg(args.password))
            print(f"Updated password for {args.username}")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
