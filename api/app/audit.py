"""Answer `audit: `-prefixed admin questions from event data only.
Fixed v1 intent allowlist; parameterized store access; never touches vectors."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from .triage import AUDIT_INTENTS, match_audit_intent

_APP_TZ = timezone(timedelta(hours=8))  # Asia/Manila (no DST; +08 fixed)


def answer_audit(question: str, store, account_id: str | None = None) -> tuple[bool, str]:
    """Returns (answered, text). answered=False -> refuse with supported list.

    account_id set => that account's events only; None => platform-wide
    (internal scope). Exception: logins are logged without an account
    (auth.py), so they always stay platform-wide or they would read 0.
    """
    intent = match_audit_intent(question)
    if intent == "uploads_today":
        n = _count_today(store, "upload", account_id)
        return True, f"Uploads today (Asia/Manila): {n}."
    if intent == "uploading_users_today":
        n = _distinct_uploaders_today(store, account_id)
        return True, f"Users who uploaded files today (Asia/Manila): {n}."
    if intent == "questions_per_account_today":
        per = _per_account(store, "question", account_id)
        body = "; ".join(f"{a}: {c}" for a, c in per.items()) or "none today"
        return True, f"Questions per account today (Asia/Manila): {body}."
    if intent == "escalations_per_department_today":
        per = _per_department(store, account_id)
        body = "; ".join(f"{d}: {c}" for d, c in per.items()) or "none today"
        return True, f"Escalations per department today (Asia/Manila): {body}."
    if intent == "logins_today":
        # No account dimension on login events — never filter these.
        n = _count_today(store, "login", None)
        return True, f"Logins today (Asia/Manila): {n}."
    return False, ("I can only answer these audit questions: "
                   + "; ".join(AUDIT_INTENTS) + ".")


def _today() -> str:
    # Real Asia/Manila day — never derived from event data (a quiet day must
    # read 0, not the previous active day's numbers).
    return datetime.now(_APP_TZ).date().isoformat()


def _day_of(ts: str) -> str | None:
    """Asia/Manila calendar day of an event timestamp (UTC instant stored)."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_APP_TZ).date().isoformat()


def _today_events(store, action: str, account_id: str | None) -> list[dict]:
    """Events for one action on the Manila today, optionally account-scoped."""
    day = _today()
    return [e for e in store.audit_query(action=action, limit=10000)
            if _day_of(e["ts"]) == day
            and (account_id is None or e.get("account_id") == account_id)]


def _count_today(store, action: str, account_id: str | None) -> int:
    return len(_today_events(store, action, account_id))


def _distinct_uploaders_today(store, account_id: str | None) -> int:
    return len({e["actor"] for e in _today_events(store, "upload", account_id)})


def _per_account(store, action: str, account_id: str | None) -> dict:
    out: dict[str, int] = {}
    for e in _today_events(store, action, account_id):
        out[e["account_id"] or "unscoped"] = out.get(e["account_id"] or "unscoped", 0) + 1
    return out


def _per_department(store, account_id: str | None) -> dict:
    out: dict[str, int] = {}
    for e in _today_events(store, "escalation", account_id):
        d = (e["detail"] or "unknown").split("department=")[-1].split()[0] \
            if "department=" in (e["detail"] or "") else "unknown"
        out[d] = out.get(d, 0) + 1
    return out
