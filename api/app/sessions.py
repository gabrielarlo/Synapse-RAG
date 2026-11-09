"""Per-session temporary context memory on SQLite FTS5.

Binding: a session is fixed to one (user_id, account_id) at creation.
TTL: `last_active` updates ONLY on inbound user messages and ONLY after the
TTL check for that message. A message > TTL after last_active wipes old
context and reports expired=True. External FAQ is stateless (never uses this).
"""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone

TTL_DEFAULT_S = 30 * 60


class SessionStore:
    def __init__(self, path: str, ttl_s: int = TTL_DEFAULT_S) -> None:
        self.path = path
        self.ttl_s = ttl_s
        self._lock = threading.Lock()  # one shared connection, threaded server
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY,"
            " user_id TEXT NOT NULL, account_id TEXT NOT NULL, last_active REAL NOT NULL)")
        self._conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS session_turns USING fts5("
            "session_id UNINDEXED, role UNINDEXED, content)")
        # Display metadata per turn (ts/category/escalated/department) keyed
        # by the FTS rowid; legacy turns simply have no row (LEFT JOIN = None).
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS session_meta(turn_id INTEGER PRIMARY KEY,"
            " ts TEXT, category TEXT, escalated INTEGER, department TEXT)")
        self._conn.commit()

    def user_message(self, session_id: str | None, user_id: str,
                     account_id: str, content: str,
                     now: float | None = None) -> tuple[str, bool, str]:
        """Record a user message. Returns (session_id, expired, context_text)."""
        now = time.time() if now is None else now
        with self._lock:
            sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
            row = self._conn.execute(
                "SELECT user_id, account_id, last_active FROM sessions WHERE session_id=?",
                (sid,)).fetchone()
            expired = False
            if row is None:
                self._conn.execute(
                    "INSERT INTO sessions(session_id, user_id, account_id, last_active)"
                    " VALUES (?,?,?,?)", (sid, user_id, account_id, now))
                context = ""
            else:
                if row[0] != user_id or row[1] != account_id:
                    raise PermissionError("session belongs to another user or account")
                expired = (now - row[2]) > self.ttl_s
                if expired:
                    self._conn.execute(
                        "DELETE FROM session_meta WHERE turn_id IN"
                        " (SELECT rowid FROM session_turns WHERE session_id=?)",
                        (sid,))
                    self._conn.execute("DELETE FROM session_turns WHERE session_id=?",
                                       (sid,))
                    context = ""
                else:
                    context = self._read_context(sid)
                self._conn.execute("UPDATE sessions SET last_active=? WHERE session_id=?",
                                   (now, sid))
            cur = self._conn.execute(
                "INSERT INTO session_turns(session_id, role, content) VALUES (?,"
                " 'user', ?)", (sid, content))
            self._insert_meta(cur.lastrowid, datetime.fromtimestamp(
                now, tz=timezone.utc).isoformat(), None, False, None)
            self._conn.commit()
            return sid, expired, context

    def assistant_message(self, session_id: str, content: str,
                          category: str | None = None, escalated: bool = False,
                          department: str | None = None) -> None:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO session_turns(session_id, role, content) VALUES (?,"
                " 'assistant', ?)", (session_id, content))
            self._insert_meta(cur.lastrowid, datetime.now(
                timezone.utc).isoformat(), category, escalated, department)
            self._conn.commit()

    def get_session(self, session_id: str) -> tuple[str, str, float] | None:
        """(user_id, account_id, last_active) for ownership checks; the
        account_id is '' for internal-scoped sessions."""
        with self._lock:
            return self._conn.execute(
                "SELECT user_id, account_id, last_active FROM sessions"
                " WHERE session_id=?", (session_id,)).fetchone()

    def list_turns(self, session_id: str, limit: int = 100) -> list[dict]:
        """Latest turns for restoring a persisted thread (chronological).

        Includes display metadata (ts/category/escalated/department) when
        present; legacy turns without a meta row return None/empty fields."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT t.role, t.content, m.ts, m.category, m.escalated,"
                " m.department FROM session_turns t LEFT JOIN session_meta m"
                " ON m.turn_id = t.rowid WHERE t.session_id=?"
                " ORDER BY t.rowid DESC LIMIT ?", (session_id, limit)).fetchall()
            return [{"role": r[0], "content": r[1], "ts": r[2],
                     "category": r[3], "escalated": bool(r[4]),
                     "department": r[5]} for r in reversed(rows)]

    def list_sessions(self, user_id: str, limit: int = 20) -> list[dict]:
        """User sessions, newest first, limited. Count/preview
        exclude audit artifacts (user 'audit: ' + assistant category='audit');
        audit-only sessions get preview='' count=0. Read-only: never touches
        last_active, never resurrects. History shows all (limited), not TTL-filtered."""
        limit = max(1, min(50, limit))
        with self._lock:
            rows = self._conn.execute(
                "SELECT session_id, account_id, last_active FROM sessions"
                " WHERE user_id=?"
                " ORDER BY last_active DESC LIMIT ?", (user_id, limit)).fetchall()
            out: list[dict] = []
            for sid, acct, last in rows:
                turns = self._conn.execute(
                    "SELECT t.role, t.content, m.category FROM session_turns t"
                    " LEFT JOIN session_meta m ON m.turn_id=t.rowid"
                    " WHERE t.session_id=? ORDER BY t.rowid ASC", (sid,)).fetchall()
                non_audit = [t for t in turns
                             if not ((t[0] == 'user' and (t[1] or '').startswith('audit: '))
                                     or t[2] == 'audit')]
                preview = next((t[1][:80] for t in non_audit if t[0] == 'user' and t[1]), '')
                out.append({"session_id": sid, "account_id": acct,
                            "last_active": last, "count": len(non_audit),
                            "preview": preview})
            return out

    def _insert_meta(self, turn_id: int, ts: str | None,
                     category: str | None, escalated: bool,
                     department: str | None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO session_meta(turn_id, ts, category,"
            " escalated, department) VALUES (?,?,?,?,?)",
            (turn_id, ts, category, int(escalated), department))

    def _read_context(self, sid: str, limit: int = 6) -> str:
        # newest turns first, then back in chronological order
        rows = self._conn.execute(
            "SELECT role, content FROM session_turns WHERE session_id=?"
            " ORDER BY rowid DESC LIMIT ?", (sid, limit)).fetchall()
        return "\n".join(f"{r}: {c}" for r, c in reversed(rows))
