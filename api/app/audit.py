"""Answer `audit: `-prefixed admin questions from event data only.
Fixed v1 intent allowlist; parameterized store access; never touches vectors."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from .triage import AUDIT_INTENTS, match_audit_intent

_APP_TZ = timezone(timedelta(hours=8))  # Asia/Manila (no DST; +08 fixed)


def answer_audit(question: str, store, account_id: str | None = None) -> tuple[bool, str]:
    """Flexible audit answering scoped to the selected account.

    account_id set => that account's events only; None => platform-wide
    (internal/global scope). Logins have no account and stay platform-wide.
    Never refuses audit-prefixed questions — always returns an answer derived
    from audit_events (no vectors, no ad-hoc SQL).
    """
    q_raw = question[len("audit:"):].strip() if question.startswith("audit:") else question
    q = q_raw.lower()
    scope_label = _scope_label(account_id)

    # Keep original allowlisted intents as fast paths (backwards compat)
    intent = match_audit_intent(question)
    if intent == "uploads_today":
        n = _count_today(store, "upload", account_id)
        return True, f"Uploads today (Asia/Manila): {n}."
    if intent == "uploading_users_today":
        n = _distinct_uploaders_today(store, account_id)
        return True, f"Users who uploaded files today (Asia/Manila): {n}."
    if intent == "questions_per_account_today":
        # When scoped to an account, show that account only; when global show per-account breakdown
        if account_id is not None:
            n = _count_today(store, "question", account_id)
            return True, f"Questions today (Asia/Manila): {n}."
        per = _per_account(store, "question", account_id)
        body = "; ".join(f"{a}: {c}" for a, c in per.items()) or "none today"
        return True, f"Questions per account today (Asia/Manila): {body}."
    if intent == "escalations_per_department_today":
        if account_id is not None:
            n = _count_today(store, "escalation", account_id)
            per = _per_department(store, account_id)
            body = "; ".join(f"{d}: {c}" for d, c in per.items()) or "none today"
            return True, f"Escalations today (Asia/Manila): {n} ({body})."
        per = _per_department(store, account_id)
        body = "; ".join(f"{d}: {c}" for d, c in per.items()) or "none today"
        return True, f"Escalations per department today (Asia/Manila): {body}."
    if intent == "logins_today":
        n = _count_today(store, "login", None)
        return True, f"Logins today (Asia/Manila): {n}."

    # --- flexible handling: latest / recent ---
    if any(k in q for k in ("latest", "last ", "most recent", "recent", "newest")):
        return True, _answer_latest(q, store, account_id, scope_label)

    # --- flexible counts for any mentioned action ---
    action_map = {
        "upload": "upload",
        "login": "login",
        "question": "question",
        "escalat": "escalation",
        "ingest": "ingest",
        "delete": "delete",
        "transfer": "transfer",
        "replace": "replace",
        "credential": "credential",
    }
    mentioned = [act for kw, act in action_map.items() if kw in q]
    # generic count words
    wants_count = any(k in q for k in ("how many", "count", "number", "total", "per day", "today", "daily"))
    if mentioned and wants_count:
        parts = []
        for act in sorted(set(mentioned)):
            acct = None if act == "login" else account_id
            n = _count_today(store, act, acct)
            parts.append(f"{act}s today{scope_label}: {n}")
        # distinct uploaders special case
        if "upload" in mentioned and any(k in q for k in ("user", "who")):
            n = _distinct_uploaders_today(store, account_id)
            parts.append(f"distinct uploading users today{scope_label}: {n}")
        return True, "; ".join(parts) + "."

    # --- full summary fallback: answer any audit-related question with data ---
    audit_keywords = ("action", "event", "audit", "activity", "summary", "overview", "happen", "doing", "show", "list", "latest", "today")
    if any(k in q for k in audit_keywords):
        return True, _answer_summary(store, account_id, scope_label)

    # unrelated audit: prefix but not audit-related -> keep old refusal for backwards compat
    return False, ("I can only answer these audit questions: "
                   + "; ".join(AUDIT_INTENTS) + ". "
                   + "Try: audit: what is the latest action? or audit: show summary today.")


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
    # scope+action pushed to store so LIMIT applies to the right slice; raise cap for busy tenants
    acct = None if action == "login" else account_id
    return [e for e in store.audit_query(action=action, account_id=acct, limit=100000)
            if _day_of(e["ts"]) == day
            and (account_id is None or e.get("account_id") == account_id or action == "login")]


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


def _scope_label(account_id: str | None) -> str:
    if account_id is None:
        return " today (Asia/Manila, platform-wide)"
    return " today (Asia/Manila, account scoped)"


def _manila_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_APP_TZ).isoformat()
    except Exception:
        return ts


def _answer_latest(q: str, store, account_id: str | None, scope_label: str) -> str:
    # detect action filter for latest — keep in sync with action_map above
    action = None
    for kw, act in (("upload", "upload"), ("login", "login"), ("question", "question"),
                    ("escalat", "escalation"), ("ingest", "ingest"),
                    ("delete", "delete"), ("transfer", "transfer"),
                    ("replace", "replace"), ("credential", "credential")):
        if kw in q:
            action = act
            break
    # logins are platform-wide
    acct = None if action == "login" else account_id
    events = store.audit_query(action=action, account_id=acct, limit=20)
    # when scoped and no action filter, filter to account (keep platform logins out)
    if account_id is not None and action is None:
        events = [e for e in events if e.get("account_id") == account_id]
    # normalize to most-recent-first (DB is DESC, memory is tail-chronological)
    events = sorted(events, key=lambda e: e.get("ts") or "", reverse=True)
    if not events:
        return f"No audit events found{scope_label}."
    # events are DESC; most recent first
    latest = events[0]
    # single latest answer
    detail = f" — {latest['detail']}" if latest.get("detail") else ""
    scope_note = " (platform-wide)" if account_id is None else " (account scoped)"
    # text is concise (single latest) — full history lives in the A2UI List
    return f"Latest action{scope_note} (Asia/Manila): {latest['action']} by {latest['actor']} at {_manila_ts(latest['ts'])}{detail}."


def _answer_summary(store, account_id: str | None, scope_label: str) -> str:
    # Build a compact today summary across key actions
    actions = ["upload", "login", "question", "escalation", "ingest"]
    parts = []
    for act in actions:
        acct = None if act == "login" else account_id
        n = _count_today(store, act, acct)
        parts.append(f"{act}s: {n}")
    # latest is scoped — query already limited to the right account so LIMIT is not wasted on platform noise
    if account_id is None:
        events = store.audit_query(action=None, account_id=None, limit=20)
    else:
        events = store.audit_query(action=None, account_id=account_id, limit=20)
    events = sorted(events, key=lambda e: e.get("ts") or "", reverse=True)
    latest_str = ""
    if events:
        e = events[0]
        latest_str = f" Latest: {e['action']} by {e['actor']} at {_manila_ts(e['ts'])}."
    return f"Audit summary{scope_label}: " + ", ".join(parts) + "." + latest_str


def get_audit_events_for_surface(question: str, store, account_id: str | None) -> list[dict]:
    """Scoped events for the A2UI surface (latest-first)."""
    q = question.lower()
    action = None
    for kw, act in (("upload", "upload"), ("login", "login"), ("question", "question"),
                    ("escalat", "escalation"), ("ingest", "ingest"),
                    ("delete", "delete"), ("transfer", "transfer"),
                    ("replace", "replace"), ("credential", "credential")):
        if kw in q:
            action = act
            break
    acct = None if action == "login" else account_id
    events = store.audit_query(action=action, account_id=acct, limit=20)
    if account_id is not None and action is None:
        events = [e for e in events if e.get("account_id") == account_id]
    return sorted(events, key=lambda e: e.get("ts") or "", reverse=True)
