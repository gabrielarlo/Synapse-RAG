"""Create the database if missing, then apply infra/migrations/*.sql in order.
Already-recorded files are skipped; files failing with already-exists errors
(pre-001-era databases) are recorded and skipped — anything else aborts.
Usage: MIGRATIONS_DIR=/infra python db_init.py (DB from DATABASE_* env)."""
import glob
import os
import sys

import psycopg
from psycopg import errors as pg_errors

CATCH_UP = (pg_errors.DuplicateTable, pg_errors.DuplicateObject,
            pg_errors.DuplicateSchema)


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if not v:
        raise SystemExit(f"{name} is required")
    return v


def main() -> None:
    host, port = os.environ.get("DATABASE_HOST", "localhost"), \
        os.environ.get("DATABASE_PORT", "5432")
    user, password = env("DATABASE_USER"), env("DATABASE_PASSWORD")
    name = env("DATABASE_NAME")
    migdir = os.environ.get("MIGRATIONS_DIR",
                            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "migrations"))
    kw = {"host": host, "port": port, "user": user, "password": password}
    print(f"target {user}@{host}:{port}/{name}")
    with psycopg.connect(**kw, dbname="postgres", autocommit=True) as admin:
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname=%s",
                               (name,)).fetchone()
        if not exists:
            admin.execute(f'CREATE DATABASE "{name}"')
            print(f"created database {name}")
        else:
            print(f"database {name} exists")
    with psycopg.connect(**kw, dbname=name, autocommit=True) as db:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY)")
        files = sorted(glob.glob(os.path.join(migdir, "*.sql")))
        if not files:
            raise SystemExit(f"no migrations in {migdir}")
        for path in files:
            fname = os.path.basename(path)
            if db.execute("SELECT 1 FROM schema_migrations WHERE name=%s",
                          (fname,)).fetchone():
                print(f"skip {fname} (recorded)")
                continue
            with open(path) as f:
                try:
                    db.execute(f.read())
                except CATCH_UP as e:
                    print(f"skip {fname} (already applied: {e.diag.sqlstate})")
                else:
                    print(f"applied {fname}")
                db.execute("INSERT INTO schema_migrations(name) VALUES (%s)"
                           " ON CONFLICT DO NOTHING", (fname,))


if __name__ == "__main__":
    sys.exit(main())
