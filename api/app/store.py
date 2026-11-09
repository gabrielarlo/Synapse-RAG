"""Storage interface. PostgresStore is prod; InMemoryStore mirrors its
scoping rules in Python for hermetic tests."""
from __future__ import annotations

import math
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

CLAIM_STALE_S = 600  # claimed jobs older than this are re-queued on next claim


@dataclass
class User:
    id: str
    username: str
    pw_hash: str
    role: str  # admin | staff
    display_name: str | None = None


@dataclass
class Scope:
    user: User | None
    account_id: str | None  # exactly one account for scoped requests
    caller: str = "internal"  # internal | external
    is_admin: bool = False


@dataclass
class Chunk:
    content: str
    embedding: list[float]
    document_id: str = ""
    account_id: str | None = None
    is_internal: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryStore:
    """Test/dev store enforcing the same scope rules as the RLS policies."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.accounts: dict[str, str] = {}
        self.staff_accounts: set[tuple[str, str]] = set()
        self.documents: dict[str, dict] = {}
        self.chunks: list[dict] = []
        self.jobs: dict[str, dict] = {}
        self.credentials: dict[str, dict] = {}
        self.events: list[dict] = []

    # -- identity --
    def create_user(self, username: str, pw_hash: str, role: str,
                    display_name: str | None = None) -> User:
        if any(u.username == username for u in self.users.values()):
            raise ValueError("username taken")
        u = User(id=str(uuid.uuid4()), username=username, pw_hash=pw_hash,
                 role=role, display_name=display_name)
        self.users[u.id] = u
        return u

    def get_user_by_name(self, username: str) -> User | None:
        return next((u for u in self.users.values() if u.username == username), None)

    def user_exists(self, user_id: str) -> bool:
        return user_id in self.users

    def account_exists(self, account_id: str) -> bool:
        return account_id in self.accounts

    def list_users(self) -> list[User]:
        return list(self.users.values())

    def create_account(self, name: str) -> dict:
        if name in self.accounts.values():
            raise ValueError("account exists")
        aid = str(uuid.uuid4())
        self.accounts[aid] = name
        return {"id": aid, "name": name}

    def list_accounts(self, scope: Scope) -> list[dict]:
        if scope.is_admin:
            return [{"id": k, "name": v} for k, v in self.accounts.items()]
        return [
            {"id": a, "name": self.accounts[a]}
            for (u, a) in self.staff_accounts
            if u == scope.user.id and a in self.accounts
        ]

    def is_member(self, user_id: str, account_id: str) -> bool:
        return (user_id, account_id) in self.staff_accounts

    def assign(self, user_id: str, account_id: str) -> None:
        if user_id not in self.users or account_id not in self.accounts:
            raise KeyError("unknown user or account")
        self.staff_accounts.add((user_id, account_id))

    def unassign(self, user_id: str, account_id: str) -> None:
        self.staff_accounts.discard((user_id, account_id))

    # -- documents / jobs --
    def create_document(self, filename: str, account_id: str | None,
                        is_internal: bool, uploaded_by: str) -> dict:
        if (account_id is None) == (not is_internal) and account_id is None:
            raise ValueError("scope required")
        if account_id is None and not is_internal:
            raise ValueError("scope required")
        did = str(uuid.uuid4())
        doc = {"id": did, "filename": filename, "account_id": account_id,
               "is_internal": is_internal, "status": "queued",
               "error": None, "uploaded_by": uploaded_by, "created_at": _now(),
               "updated_at": _now(),
               "version": 1, "category": None}
        self.documents[did] = doc
        jid = str(uuid.uuid4())
        self.jobs[jid] = {"id": jid, "document_id": did, "account_id": account_id,
                          "is_internal": is_internal, "status": "pending",
                          "attempts": 0, "error": None}
        return {"document": doc, "job_id": jid}

    def get_document(self, document_id: str) -> dict | None:
        return self.documents.get(document_id)

    def replace_document(self, document_id: str, filename: str | None) -> dict | None:
        """Replace content: bump version, drop old vectors and jobs, queue a new
        job carrying the document's scope. None when the document is gone."""
        d = self.documents.get(document_id)
        if d is None:
            return None
        d["version"] += 1
        if filename:
            d["filename"] = filename
        d["updated_at"] = _now()
        d["status"], d["error"], d["category"] = "queued", None, None
        self.chunks = [c for c in self.chunks if c["document_id"] != document_id]
        for jid in [k for k, j in self.jobs.items() if j["document_id"] == document_id]:
            del self.jobs[jid]
        jid = str(uuid.uuid4())
        self.jobs[jid] = {"id": jid, "document_id": document_id,
                          "account_id": d["account_id"],
                          "is_internal": d["is_internal"], "status": "pending",
                          "attempts": 0, "error": None}
        return {"job_id": jid, "version": d["version"], "filename": d["filename"],
                "updated_at": d["updated_at"]}

    def delete_document(self, document_id: str) -> str | None:
        """Remove document + vectors + jobs; returns the filename, None if gone."""
        d = self.documents.pop(document_id, None)
        if d is None:
            return None
        self.chunks = [c for c in self.chunks if c["document_id"] != document_id]
        for jid in [k for k, j in self.jobs.items() if j["document_id"] == document_id]:
            del self.jobs[jid]
        return d["filename"]

    def document_content(self, document_id: str, limit: int = 50) -> dict:
        """Ordered chunk text for the read-only view, capped for payload size."""
        rows = sorted((c for c in self.chunks if c["document_id"] == document_id),
                      key=lambda c: c["ord"])
        return {"chunks": [c["content"] for c in rows[:limit]], "total": len(rows)}

    def list_documents(self, scope: Scope) -> list[dict]:
        # exactly one scope for every role: an account's docs, or internal
        # docs (management authorization is where admin bypass applies)
        out = []
        for d in self.documents.values():
            if scope.account_id is not None and d["account_id"] == scope.account_id:
                out.append(d)
            elif scope.account_id is None and scope.caller == "internal" \
                    and d["is_internal"]:
                out.append(d)
        return out

    def claim_job(self) -> dict | None:
        now = time.time()
        for j in self.jobs.values():
            if j["status"] == "claimed" and now - j.get("updated_at", now) > CLAIM_STALE_S:
                j["status"] = "pending"  # worker died mid-job; re-queue
        for j in self.jobs.values():
            if j["status"] == "pending":
                j["status"] = "claimed"
                j["attempts"] += 1
                j["updated_at"] = now
                out = dict(j)
                out["filename"] = self.documents[j["document_id"]]["filename"]
                return out
        return None

    def finish_job(self, job_id: str, ok: bool, error: str | None = None,
                   category: str | None = None,
                   document_id: str | None = None) -> bool:
        """Job-gated finish: False (no writes) when the job was superseded."""
        j = self.jobs.get(job_id)
        if j is None or (document_id and j["document_id"] != document_id):
            return False
        j["status"] = "ready" if ok else "failed"
        j["error"] = error
        d = self.documents[j["document_id"]]
        d["status"] = "ready" if ok else "failed"
        d["error"] = error
        if ok and category is not None:
            d["category"] = category
        return True

    def add_chunks(self, document_id: str, chunks: list[Chunk],
                   job_id: str | None = None) -> None:
        d = self.documents.get(document_id)
        if d is None:
            raise ValueError("unknown document")
        if job_id is not None:
            j = self.jobs.get(job_id)
            if j is None or j["document_id"] != document_id:
                raise ValueError("stale job")  # replaced/deleted mid-ingest
            self.chunks = [c for c in self.chunks
                           if c["document_id"] != document_id]
        for i, c in enumerate(chunks):
            self.chunks.append({"document_id": document_id,
                                "account_id": d["account_id"],
                                "is_internal": d["is_internal"],
                                "ord": i, "content": c.content,
                                "embedding": c.embedding})

    def search(self, embedding: list[float], scope: Scope, limit: int = 5) -> list[dict]:
        scored = []
        for c in self.chunks:
            if scope.account_id is not None:
                if c["account_id"] != scope.account_id:
                    continue
            elif scope.caller != "internal" or not c["is_internal"]:
                continue
            scored.append((cosine(embedding, c["embedding"]), c))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [dict(c, category=self.documents.get(c["document_id"], {}).get("category"))
                for _, c in scored[:limit]]

    # -- external credentials --
    def issue_credential(self, account_id: str, secret_hash: str) -> str:
        key_id = "sk_" + secrets.token_urlsafe(9)
        self.credentials[key_id] = {"key_id": key_id, "account_id": account_id,
                                    "secret_hash": secret_hash, "revoked": False,
                                    "created_at": _now()}
        return key_id

    def get_credential(self, key_id: str) -> dict | None:
        return self.credentials.get(key_id)

    def rotate_credential(self, key_id: str, new_hash: str) -> dict:
        c = self.credentials[key_id]
        c["secret_hash"] = new_hash
        c["revoked"] = False
        return c

    def revoke_credential(self, key_id: str) -> None:
        self.credentials[key_id]["revoked"] = True

    # -- audit --
    def log(self, actor: str, action: str, account_id: str | None = None,
            detail: str | None = None) -> None:
        self.events.append({"ts": _now(), "actor": actor, "action": action,
                            "account_id": account_id, "detail": detail})

    def audit_query(self, action: str | None = None, account_id: str | None = None,
                    limit: int = 100) -> list[dict]:
        out = [e for e in self.events
               if (action is None or e["action"] == action)
               and (account_id is None or e["account_id"] == account_id)]
        return out[-limit:]

    def count(self, action: str, detail_match: str | None = None,
              account_id: str | None = None, today: bool = False) -> int:
        day = _now()[:10]
        n = 0
        for e in self.events:
            if e["action"] != action:
                continue
            if account_id is not None and e["account_id"] != account_id:
                continue
            if today and not e["ts"].startswith(day):
                continue
            if detail_match is not None and detail_match not in (e["detail"] or ""):
                continue
            n += 1
        return n
