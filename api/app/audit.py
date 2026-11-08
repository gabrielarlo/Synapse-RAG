"""Answer `audit: `-prefixed admin questions from event data only.
Fixed v1 intent allowlist; parameterized store access; never touches vectors."""
from __future__ import annotations

from datetime import datetime, timezone

from .triage import AUDIT_INTENTS, match_audit_intent


def answer_audit(question: str, store) -> tuple[bool, str]:
    """Returns (answered, text). answered=False -> refuse with supported list."""
    intent = match_audit_intent(question)
    if intent == "uploads_today":
        n = store.count("upload", today=True)
        return True, f"Uploads today (UTC): {n}."
    if intent == "uploading_users_today":
        n = _distinct_uploaders_today(store)
        return True, f"Users who uploaded files today (UTC): {n}."
    if intent == "questions_per_account_today":
        per = _per_account(store, "question")
        body = "; ".join(f"{a}: {c}" for a, c in per.items()) or "none today"
        return True, f"Questions per account today (UTC): {body}."
    if intent == "escalations_per_department_today":
        per = _per_department(store)
        body = "; ".join(f"{d}: {c}" for d, c in per.items()) or "none today"
        return True, f"Escalations per department today (UTC): {body}."
    if intent == "logins_today":
        n = store.count("login", today=True)
        return True, f"Logins today (UTC): {n}."
    return False, ("I can only answer these audit questions: "
                   + "; ".join(AUDIT_INTENTS) + ".")


def _today() -> str:
    # Real UTC day — never derived from event data (a quiet day must read 0,
    # not the previous active day's numbers).
    return datetime.now(timezone.utc).date().isoformat()


def _distinct_uploaders_today(store) -> int:
    day = _today()
    return len({e["actor"] for e in store.audit_query(action="upload", limit=10000)
                if e["ts"][:10] == day})


def _per_account(store, action: str) -> dict:
    day = _today()
    out: dict[str, int] = {}
    for e in store.audit_query(action=action, limit=10000):
        if e["ts"][:10] == day:
            out[e["account_id"] or "unscoped"] = out.get(e["account_id"] or "unscoped", 0) + 1
    return out


def _per_department(store) -> dict:
    day = _today()
    out: dict[str, int] = {}
    for e in store.audit_query(action="escalation", limit=10000):
        if e["ts"][:10] == day:
            d = (e["detail"] or "unknown").split("department=")[-1].split()[0] \
                if "department=" in (e["detail"] or "") else "unknown"
            out[d] = out.get(d, 0) + 1
    return out
