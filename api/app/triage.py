"""Decision-model triage parsing with safe fallback + audit intent allowlist."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass
class Triage:
    category: str
    escalate: bool
    department: str | None


def _dept(v) -> str | None:
    return v if v is None or isinstance(v, str) else str(v)


def parse_triage(raw: str) -> Triage:
    """Strict JSON parse; unparseable output falls back to a non-escalated
    general query (drift-safe, logged by the caller)."""
    try:
        j = json.loads(raw)
        return Triage(category=str(j.get("category", "general")),
                      escalate=bool(j.get("escalate", False)),
                      department=_dept(j.get("department")))
    except (json.JSONDecodeError, AttributeError, TypeError):
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            try:
                j = json.loads(m.group(0))
                return Triage(category=str(j.get("category", "general")),
                              escalate=bool(j.get("escalate", False)),
                              department=_dept(j.get("department")))
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass
        return Triage(category="general", escalate=False, department=None)


AUDIT_INTENTS = (
    "uploads count per day",
    "active uploading users per day",
    "questions count per account per day",
    "escalation count per department per day",
    "login count per day",
)


def match_audit_intent(text: str) -> str | None:
    """Map an `audit: ` question to a v1 allowlisted intent, else None."""
    t = text[len("audit:"):].strip().lower()
    if re.search(r"how many .*upload.*(today|per day|each day|daily)", t) and \
            "user" not in t:
        return "uploads_today"
    if re.search(r"how many users?.*(upload|uploads|uploading)", t):
        return "uploading_users_today"
    if re.search(r"how many questions?", t):
        return "questions_per_account_today"
    if re.search(r"escalat", t):
        return "escalations_per_department_today"
    if re.search(r"logins?|sign.?ins?|log ?ins?", t):
        return "logins_today"
    return None
