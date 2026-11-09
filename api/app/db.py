"""Postgres store: same interface as InMemoryStore, RLS enforced by PG.
Every operation runs in its own transaction with SET LOCAL scope vars."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
import re
import time

import psycopg
from psycopg_pool import ConnectionPool

from .store import Chunk, Scope, User


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _is_uuid(v: str) -> bool:
    return bool(_UUID_RE.match(v))


class PostgresStore:
    def __init__(self, dsn: str, connect_tries: int = 2,
                 connect_delay_s: float = 1.0) -> None:
        # Retry at boot: in compose, external PG may not be reachable yet.
        # Verifies with SELECT 1 — pool creation alone is lazy and proves nothing.
        last: Exception | None = None
        for _ in range(max(connect_tries, 1)):
            try:
                pool = ConnectionPool(dsn, min_size=1, max_size=10, open=True,
                                      timeout=5)
                with pool.connection() as conn, conn.cursor() as cur:
                    cur.execute("SELECT 1")
                self.pool = pool
                return
            except Exception as e:  # noqa: BLE001 — boot-time backoff
                last = e
                try:
                    pool.close()
                except Exception:
                    pass
                time.sleep(connect_delay_s)
        raise last  # type: ignore[misc]

    @contextmanager
    def _tx(self, account_id: str | None = None, caller: str = "internal",
            is_admin: bool = False) -> Iterator[psycopg.Connection]:
        # NOTE: SET LOCAL takes no bind parameters, so values are interpolated
        # after strict validation (uuid / fixed enums only — never user text).
        if account_id and not _is_uuid(account_id):
            raise ValueError("bad account_id")
        if caller not in ("internal", "external"):
            raise ValueError("bad caller")
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SET LOCAL app.current_account = '{account_id or ''}'")
                cur.execute(f"SET LOCAL app.caller = '{caller}'")
                cur.execute(f"SET LOCAL app.is_admin = '{'1' if is_admin else '0'}'")
                yield conn
            conn.commit()

    def _s(self, scope: Scope) -> dict:
        return {"account_id": scope.account_id, "caller": scope.caller,
                "is_admin": scope.is_admin}

    # -- identity --
    def create_user(self, username: str, pw_hash: str, role: str,
                    display_name: str | None = None) -> User:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users(username, pw_hash, role, display_name)"
                    " VALUES (%s,%s,%s,%s)"
                    " RETURNING id, username, pw_hash, role, display_name",
                    (username, pw_hash, role, display_name))
            except psycopg.errors.UniqueViolation:
                raise ValueError("username taken")
            r = cur.fetchone()
            return User(id=str(r[0]), username=r[1], pw_hash=r[2], role=r[3],
                        display_name=r[4])

    def get_user_by_name(self, username: str) -> User | None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, username, pw_hash, role, display_name FROM users"
                        " WHERE username=%s", (username,))
            r = cur.fetchone()
            return User(id=str(r[0]), username=r[1], pw_hash=r[2], role=r[3],
                        display_name=r[4]) if r else None

    def list_users(self) -> list[User]:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, username, pw_hash, role, display_name FROM users"
                        " ORDER BY username")
            return [User(id=str(r[0]), username=r[1], pw_hash=r[2], role=r[3],
                         display_name=r[4]) for r in cur.fetchall()]

    def create_account(self, name: str) -> dict:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO accounts(name) VALUES (%s) RETURNING id, name",
                            (name,))
            except psycopg.errors.UniqueViolation:
                raise ValueError("account exists")
            r = cur.fetchone()
            return {"id": str(r[0]), "name": r[1]}

    def list_accounts(self, scope: Scope) -> list[dict]:
        if scope.is_admin:
            with self._tx(is_admin=True) as conn, conn.cursor() as cur:
                cur.execute("SELECT id, name FROM accounts ORDER BY name")
                return [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]
        with self._tx(**self._s(scope)) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT a.id, a.name FROM accounts a JOIN staff_accounts s"
                " ON s.account_id = a.id WHERE s.user_id = %s ORDER BY a.name",
                (scope.user.id,))
            return [{"id": str(r[0]), "name": r[1]} for r in cur.fetchall()]

    def user_exists(self, user_id: str) -> bool:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE id=%s", (user_id,))
            return cur.fetchone() is not None

    def account_exists(self, account_id: str) -> bool:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM accounts WHERE id=%s", (account_id,))
            return cur.fetchone() is not None

    def is_member(self, user_id: str, account_id: str) -> bool:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM staff_accounts WHERE user_id=%s AND account_id=%s",
                        (user_id, account_id))
            return cur.fetchone() is not None

    def assign(self, user_id: str, account_id: str) -> None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO staff_accounts(user_id, account_id) VALUES (%s,%s)"
                        " ON CONFLICT DO NOTHING", (user_id, account_id))

    def unassign(self, user_id: str, account_id: str) -> None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM staff_accounts WHERE user_id=%s AND account_id=%s",
                        (user_id, account_id))

    # -- documents / jobs --
    def create_document(self, filename: str, account_id: str | None,
                        is_internal: bool, uploaded_by: str) -> dict:
        if account_id is None and not is_internal:
            raise ValueError("scope required")
        with self._tx(account_id, is_admin=True) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents(account_id, is_internal, filename, uploaded_by)"
                " VALUES (%s,%s,%s,%s) RETURNING id, filename, account_id, is_internal,"
                " status, error, uploaded_by, created_at, updated_at, version, category",
                (account_id, is_internal, filename, uploaded_by))
            r = cur.fetchone()
            doc = {"id": str(r[0]), "filename": r[1],
                   "account_id": str(r[2]) if r[2] else None, "is_internal": r[3],
                   "status": r[4], "error": r[5], "uploaded_by": str(r[6]),
                   "created_at": r[7].isoformat(), "updated_at": r[8].isoformat(),
                   "version": r[9], "category": r[10]}
            cur.execute(
                "INSERT INTO ingestion_jobs(document_id, account_id, is_internal)"
                " VALUES (%s,%s,%s) RETURNING id",
                (doc["id"], account_id, is_internal))
            return {"document": doc, "job_id": str(cur.fetchone()[0])}

    def document_content(self, document_id: str, limit: int = 50) -> dict:
        """Ordered chunk text for the read-only view, capped for payload size."""
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT content, count(*) OVER () FROM chunks"
                        " WHERE document_id=%s ORDER BY ord LIMIT %s",
                        (document_id, limit))
            rows = cur.fetchall()
            return {"chunks": [r[0] for r in rows],
                    "total": rows[0][1] if rows else 0}

    def list_documents(self, scope: Scope) -> list[dict]:
        with self._tx(**self._s(scope)) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, filename, account_id, is_internal, status, error,"
                        " uploaded_by, created_at, updated_at, version, category FROM documents"
                        " ORDER BY created_at DESC")
            return [{"id": str(r[0]), "filename": r[1],
                     "account_id": str(r[2]) if r[2] else None, "is_internal": r[3],
                     "status": r[4], "error": r[5],
                     "uploaded_by": str(r[6]) if r[6] else None,
                     "created_at": r[7].isoformat(),
                     "updated_at": r[8].isoformat() if r[8] else None,
                     "version": r[9], "category": r[10]} for r in cur.fetchall()]

    def get_document(self, document_id: str) -> dict | None:
        # admin-scoped: authz reads must see internal and account docs alike
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, filename, account_id, is_internal, uploaded_by,"
                        " status, version, category, created_at, updated_at"
                        " FROM documents WHERE id=%s",
                        (document_id,))
            r = cur.fetchone()
            return {"id": str(r[0]), "filename": r[1],
                    "account_id": str(r[2]) if r[2] else None, "is_internal": r[3],
                    "uploaded_by": str(r[4]) if r[4] else None, "status": r[5],
                    "version": r[6], "category": r[7],
                    "created_at": r[8].isoformat() if r[8] else None,
                    "updated_at": r[9].isoformat() if r[9] else None} if r else None

    def replace_document(self, document_id: str, filename: str | None) -> dict | None:
        """Replace content: bump version (takes the row lock first), drop old
        vectors/jobs, queue a new job carrying the document's scope."""
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET version=version+1,"
                " filename=COALESCE(%s, filename), status='queued', error=NULL,"
                " category=NULL, updated_at=now() WHERE id=%s"
                " RETURNING id, filename, version, updated_at",
                (filename, document_id))
            r = cur.fetchone()
            if r is None:
                return None
            cur.execute("DELETE FROM chunks WHERE document_id=%s", (document_id,))
            cur.execute("DELETE FROM ingestion_jobs WHERE document_id=%s",
                        (document_id,))
            cur.execute(
                "INSERT INTO ingestion_jobs(document_id, account_id, is_internal)"
                " SELECT id, account_id, is_internal FROM documents WHERE id=%s"
                " RETURNING id", (document_id,))
            return {"job_id": str(cur.fetchone()[0]), "version": r[2],
                    "filename": r[1],
                    "updated_at": r[3].isoformat() if r[3] else None}

    def delete_document(self, document_id: str) -> str | None:
        # doc row locked first; chunks/jobs go via FK cascade
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id=%s RETURNING filename",
                        (document_id,))
            r = cur.fetchone()
            return r[0] if r else None

    def claim_job(self) -> dict | None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            from .store import CLAIM_STALE_S
            cur.execute(
                "UPDATE ingestion_jobs SET status='pending', updated_at=now()"
                " WHERE status='claimed' AND updated_at < now() - make_interval(secs=>%s)",
                (CLAIM_STALE_S,))
            cur.execute(
                "SELECT j.id, j.document_id, j.account_id, j.is_internal, j.status,"
                " j.attempts, d.filename FROM ingestion_jobs j"
                " JOIN documents d ON d.id = j.document_id"
                " WHERE j.status='pending' ORDER BY j.created_at"
                " FOR UPDATE OF j SKIP LOCKED LIMIT 1")
            r = cur.fetchone()
            if not r:
                return None
            cur.execute("UPDATE ingestion_jobs SET status='claimed', attempts=attempts+1,"
                        " updated_at=now() WHERE id=%s", (r[0],))
            return {"id": str(r[0]), "document_id": str(r[1]),
                    "account_id": str(r[2]) if r[2] else None, "is_internal": r[3],
                    "status": "claimed", "attempts": r[5] + 1, "filename": r[6]}

    def finish_job(self, job_id: str, ok: bool, error: str | None = None,
                   category: str | None = None,
                   document_id: str | None = None) -> bool:
        """Job-gated finish. Locks the document first (lock invariant), then
        updates the job only if it still exists for that document. Returns
        False and writes nothing when the job was superseded."""
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            if document_id is None:
                # unlocked read; no row lock, so the doc-first order holds
                cur.execute("SELECT document_id FROM ingestion_jobs WHERE id=%s",
                            (job_id,))
                r = cur.fetchone()
                if r is None:
                    return False
                document_id = str(r[0])
            cur.execute("SELECT id FROM documents WHERE id=%s FOR UPDATE",
                        (document_id,))
            if cur.fetchone() is None:
                return False
            cur.execute("UPDATE ingestion_jobs SET status=%s, error=%s,"
                        " updated_at=now() WHERE id=%s AND document_id=%s"
                        " RETURNING id",
                        ("ready" if ok else "failed", error, job_id, document_id))
            if cur.fetchone() is None:
                return False
            cur.execute("UPDATE documents SET status=%s, error=%s,"
                        " category=COALESCE(%s, category) WHERE id=%s",
                        ("ready" if ok else "failed", error,
                         category if ok else None, document_id))
            return True

    def add_chunks(self, document_id: str, chunks: list[Chunk],
                   job_id: str | None = None) -> None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT account_id, is_internal FROM documents"
                        " WHERE id=%s FOR UPDATE", (document_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("unknown document")
            acct, internal = row
            if job_id is not None:
                cur.execute("SELECT 1 FROM ingestion_jobs WHERE id=%s"
                            " AND document_id=%s", (job_id, document_id))
                if cur.fetchone() is None:
                    raise ValueError("stale job")  # replaced/deleted mid-ingest
                cur.execute("DELETE FROM chunks WHERE document_id=%s",
                            (document_id,))
            for i, c in enumerate(chunks):
                cur.execute(
                    "INSERT INTO chunks(document_id, account_id, is_internal, ord,"
                    " content, embedding) VALUES (%s,%s,%s,%s,%s,%s::vector)",
                    (document_id, acct, internal, i, c.content,
                     "[" + ",".join(map(str, c.embedding)) + "]"))

    def search(self, embedding: list[float], scope: Scope, limit: int = 5) -> list[dict]:
        with self._tx(**self._s(scope)) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT c.document_id, c.account_id, c.is_internal, c.content,"
                " d.category FROM chunks c"
                " LEFT JOIN documents d ON d.id = c.document_id"
                " ORDER BY c.embedding <=> %s::vector LIMIT %s",
                ("[" + ",".join(map(str, embedding)) + "]", limit))
            return [{"document_id": str(r[0]),
                     "account_id": str(r[1]) if r[1] else None,
                     "is_internal": r[2], "content": r[3],
                     "category": r[4]} for r in cur.fetchall()]

    # -- external credentials (system lookups run admin-scoped) --
    def issue_credential(self, account_id: str, secret_hash: str) -> str:
        import secrets as _s
        key_id = "sk_" + _s.token_urlsafe(9)
        with self._tx(account_id, is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO api_credentials(key_id, account_id, secret_hash)"
                        " VALUES (%s,%s,%s)", (key_id, account_id, secret_hash))
            return key_id

    def get_credential(self, key_id: str) -> dict | None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT key_id, account_id, secret_hash, revoked, created_at"
                        " FROM api_credentials WHERE key_id=%s", (key_id,))
            r = cur.fetchone()
            return {"key_id": r[0], "account_id": str(r[1]), "secret_hash": r[2],
                    "revoked": r[3], "created_at": r[4].isoformat()} if r else None

    def rotate_credential(self, key_id: str, new_hash: str) -> dict:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("UPDATE api_credentials SET secret_hash=%s, revoked=FALSE"
                        " WHERE key_id=%s RETURNING key_id, account_id, created_at",
                        (new_hash, key_id))
            r = cur.fetchone()
            return {"key_id": r[0], "account_id": str(r[1]),
                    "created_at": r[2].isoformat()}

    def revoke_credential(self, key_id: str) -> None:
        with self._tx(is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("UPDATE api_credentials SET revoked=TRUE WHERE key_id=%s",
                        (key_id,))

    # -- audit --
    def log(self, actor: str, action: str, account_id: str | None = None,
            detail: str | None = None) -> None:
        with self._tx(account_id, is_admin=True) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO audit_events(actor, action, account_id, detail)"
                        " VALUES (%s,%s,%s,%s)", (actor, action, account_id, detail))

    def audit_query(self, action: str | None = None, account_id: str | None = None,
                    limit: int = 100) -> list[dict]:
        with self._tx(account_id, is_admin=True) as conn, conn.cursor() as cur:
            q = ("SELECT ts, actor, action, account_id, detail FROM audit_events"
                 " WHERE (%s::text IS NULL OR action=%s)"
                 " AND (%s::text IS NULL OR account_id=%s::uuid)"
                 " ORDER BY ts DESC LIMIT %s")
            cur.execute(q, (action, action, account_id, account_id, limit))
            return [{"ts": r[0].isoformat(), "actor": r[1], "action": r[2],
                     "account_id": str(r[3]) if r[3] else None, "detail": r[4]}
                    for r in cur.fetchall()]

    def count(self, action: str, detail_match: str | None = None,
              account_id: str | None = None, today: bool = False) -> int:
        with self._tx(account_id, is_admin=True) as conn, conn.cursor() as cur:
            q = ("SELECT count(*) FROM audit_events WHERE action=%s"
                 " AND (%s::text IS NULL OR detail LIKE '%%'||%s||'%%')"
                 " AND (%s::text IS NULL OR account_id=%s::uuid)"
                 " AND (NOT %s OR ts::date = CURRENT_DATE)")
            cur.execute(q, (action, detail_match, detail_match, account_id, account_id,
                            today))
            return cur.fetchone()[0]  # type: ignore[return-value]
