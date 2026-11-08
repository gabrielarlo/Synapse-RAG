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
                    self._conn.execute("DELETE FROM session_turns WHERE session_id=?",
                                       (sid,))
                    context = ""
                else:
                    context = self._read_context(sid)
                self._conn.execute("UPDATE sessions SET last_active=? WHERE session_id=?",
                                   (now, sid))
            self._conn.execute(
                "INSERT INTO session_turns(session_id, role, content) VALUES (?,"
                " 'user', ?)", (sid, content))
            self._conn.commit()
            return sid, expired, context

    def assistant_message(self, session_id: str, content: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO session_turns(session_id, role, content) VALUES (?,"
                " 'assistant', ?)", (session_id, content))
            self._conn.commit()

    def _read_context(self, sid: str, limit: int = 6) -> str:
        # newest turns first, then back in chronological order
        rows = self._conn.execute(
            "SELECT role, content FROM session_turns WHERE session_id=?"
            " ORDER BY rowid DESC LIMIT ?", (sid, limit)).fetchall()
        return "\n".join(f"{r}: {c}" for r, c in reversed(rows))
