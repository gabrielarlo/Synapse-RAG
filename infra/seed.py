"""Seed the first admin user. Idempotent: skips if the username exists.
Usage: SEED_ADMIN_NAME=... SEED_ADMIN_USER=... SEED_ADMIN_PASS=... python infra/seed.py
DB comes from the DATABASE_* settings (same .env as the API).
"""
import os
import sys

sys.path.insert(0, _api_dir := os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "..", "api"))
if not os.path.isdir(_api_dir):
    # container layout: seed.py sits beside the app/ package (/srv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import load_settings  # noqa: E402
from app.db import PostgresStore  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> None:
    settings = load_settings()
    username = os.environ.get("SEED_ADMIN_USER", "admin")
    password = os.environ.get("SEED_ADMIN_PASS", "")
    display_name = os.environ.get("SEED_ADMIN_NAME")
    if not password:
        raise SystemExit("SEED_ADMIN_PASS is required")
    store = PostgresStore(settings.database_dsn)
    if store.get_user_by_name(username):
        print(f"user {username!r} already exists, skipping")
        return
    u = store.create_user(username, hash_password(password), "admin", display_name)
    print(f"created admin {u.username} ({u.id})")


if __name__ == "__main__":
    main()
