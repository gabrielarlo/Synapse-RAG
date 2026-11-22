"""A2UI (Agent-to-UI) helpers for the Chat channel.

Google's A2UI is a declarative, catalog-gated generative UI spec: the agent
emits JSON describing surfaces/components + a dataModel, the client renders
native widgets. This module builds a minimal spec-compliant surface for each
chat turn from retrieval + triage signals. The catalog is enforced on both
sides; the client never executes arbitrary code.

Spec refs: a2ui.org — Surface, Component, Catalog, DataModel, bindings.
We ship a single surface per assistant turn: answer + citations + escalation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

# Catalog allowlist — client renders only these types. Agent cannot request
# anything outside it (safe like data, expressive like code).
CATALOG = {
    "Card": {"props": ["title", "subtitle", "variant"]},
    "Text": {"props": ["text", "variant"]},
    "Badge": {"props": ["label", "variant"]},
    "Button": {"props": ["label", "action", "variant"]},
    "List": {"props": ["title", "items"]},
    "Sources": {"props": ["items"]},
}

ALLOWED_TYPES = set(CATALOG)


def _sanitize_component(c: dict) -> dict | None:
    """Allowlist gate: drop unknown types or non-dict entries."""
    if not isinstance(c, dict):
        return None
    t = c.get("type")
    if t not in ALLOWED_TYPES:
        return None
    # shallow copy, keep only known keys
    out: dict = {"id": str(c.get("id", "")), "type": t}
    if "props" in c and isinstance(c["props"], dict):
        out["props"] = c["props"]
    if "children" in c and isinstance(c["children"], list):
        children = [_sanitize_component(x) for x in c["children"]]
        out["children"] = [x for x in children if x is not None]
    return out


def sanitize_surface(surface: dict | None) -> dict | None:
    """Server-side re-validation of any agent-emitted A2UI (defensive)."""
    if not surface or not isinstance(surface, dict):
        return None
    comps = surface.get("components")
    if not isinstance(comps, list):
        return None
    clean = [_sanitize_component(c) for c in comps]
    clean = [c for c in clean if c is not None]
    if not clean:
        return None
    out: dict = {
        "surfaceId": str(surface.get("surfaceId", "chat")),
        "components": clean,
    }
    if isinstance(surface.get("dataModel"), dict):
        out["dataModel"] = surface["dataModel"]
    return out


def build_chat_surface(
    *,
    session_id: str | None,
    answer: str,
    chunks: list[dict],
    category: str,
    escalated: bool,
    department: str | None,
) -> dict | None:
    """Deterministic surface from retrieval + triage. Returns None when no
    supplemental UI is warranted (plain text suffices). Callers may also
    merge in an LLM-emitted surface — sanitize it first and union components."""
    components: list[dict] = []

    # Escalation banner — highest priority
    if escalated:
        components.append({
            "id": "escalation",
            "type": "Card",
            "props": {
                "title": f"Escalated to {department or 'support'}",
                "subtitle": f"Category: {category}",
                "variant": "warning",
            },
            "children": [
                {"id": "esc-text", "type": "Text",
                 "props": {"text": "A human teammate will follow up. Your question was logged.", "variant": "muted"}},
                {"id": "esc-action", "type": "Button",
                 "props": {"label": "Ask a follow-up", "variant": "primary",
                           "action": {"type": "suggest", "question": "Can you summarize the next steps?"}}},
            ],
        })

    # Citations — List of source snippets (scoped, never leaks other tenants)
    if chunks:
        seen = []
        for c in chunks[:5]:
            # content is already scope-filtered by retrieve(); trim for UI
            snippet = (c.get("content") or "")[:180].strip()
            if snippet:
                seen.append({
                    "snippet": snippet,
                    "category": c.get("category") or category,
                    "document_id": c.get("document_id", "")[:8],
                })
        if seen:
            components.append({
                "id": "sources",
                "type": "Sources",
                "props": {"items": seen},
            })
        # Category badge when retrieval agrees
        cats = {c.get("category") for c in chunks if c.get("category")}
        if len(cats) == 1:
            cat = next(iter(cats))
            components.append({
                "id": "category-badge",
                "type": "Badge",
                "props": {"label": cat, "variant": "neutral"},
            })

    if not components:
        return None

    return {
        "surfaceId": f"chat-{session_id or 'new'}",
        "components": components,
        "dataModel": {"category": category, "escalated": escalated, "department": department},
    }


def build_audit_surface(
    *,
    session_id: str | None,
    question: str,
    answer: str,
    events: list[dict],
    scope_label: str = "",
) -> dict | None:
    """Declarative surface for audit answers (latest / summary / counts).

    Rendered as a Card + List so the UI does not show a flat semicolon blob.
    Uses only catalog types (Card, List, Text, Badge)."""
    if not events and "latest" not in question.lower() and "summary" not in question.lower():
        return None
    # pick a title from the question
    ql = question.lower()
    if "latest" in ql or "recent" in ql or "newest" in ql or "last" in ql:
        # text stays singular; A2UI carries the full recent list (A2UIRenderer only supports List at top level, not nested in Card)
        if "platform-wide" in scope_label:
            subtitle = "Asia/Manila · platform-wide (internal)"
        elif "account" in scope_label:
            subtitle = "Asia/Manila · account scoped"
        else:
            subtitle = "Asia/Manila"
        items = []
        _tz = timezone(timedelta(hours=8))
        for e in events[:5]:
            ts = e.get("ts") or ""
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts_s = dt.astimezone(_tz).strftime("%m-%d %H:%M")
            except Exception:
                ts_s = ts[:16]
            detail = f" — {e['detail']}" if e.get("detail") else ""
            items.append(f"{e['action']} by {e['actor']} · {ts_s}{detail}")
        if not items:
            items = ["No audit events found."]
        return {
            "surfaceId": f"audit-{session_id or 'new'}",
            "components": [
                {
                    "id": "audit-latest",
                    "type": "Card",
                    "props": {"title": "Latest action", "subtitle": subtitle, "variant": "default"},
                    "children": [
                        {"id": "audit-highlight", "type": "Text", "props": {"text": items[0], "variant": "default"}},
                    ],
                },
                {"id": "audit-list", "type": "List", "props": {"title": f"Recent ({len(items)})", "items": items}},
            ],
            "dataModel": {"category": "audit", "scope": scope_label.strip(), "question": question, "answer": answer},
        }
    if "summary" in ql or "overview" in ql or "happen" in ql or "audit" in ql:
        # summary: Card + List of counts if present, else just text
        return {
            "surfaceId": f"audit-{session_id or 'new'}",
            "components": [
                {
                    "id": "audit-summary",
                    "type": "Card",
                    "props": {"title": "Audit summary", "subtitle": scope_label.strip(" :") or "Asia/Manila", "variant": "default"},
                    "children": [
                        {"id": "audit-text", "type": "Text", "props": {"text": answer, "variant": "default"}},
                    ],
                }
            ],
            "dataModel": {"category": "audit", "scope": scope_label.strip(), "question": question},
        }
    return None


def extract_a2ui_from_text(text: str) -> tuple[str, dict | None]:
    """If the generator emitted a ```a2ui JSON fence, extract and sanitize it,
    return (clean_text, surface). The fence is stripped from the displayed text
    so the chat stays readable when A2UI is not supported."""
    if "```a2ui" not in text:
        return text, None
    try:
        start = text.index("```a2ui")
        fence_start = text.index("\n", start)
        end = text.index("```", fence_start + 1)
        raw = text[fence_start + 1:end].strip()
        surface = sanitize_surface(json.loads(raw))
        clean = (text[:start] + text[end + 3:]).strip()
        return clean, surface
    except Exception:
        return text, None


def merge_surfaces(a: dict | None, b: dict | None) -> dict | None:
    """Union two surfaces' components; dataModel from b wins on key collision."""
    if not a:
        return b
    if not b:
        return a
    comps = list(a.get("components", [])) + list(b.get("components", []))
    # dedupe by id, keep first
    seen: set[str] = set()
    uniq: list[dict] = []
    for c in comps:
        cid = c.get("id")
        if cid not in seen:
            seen.add(cid)
            uniq.append(c)
    dm = {**(a.get("dataModel") or {}), **(b.get("dataModel") or {})}
    return {"surfaceId": b.get("surfaceId") or a.get("surfaceId"), "components": uniq, "dataModel": dm}
