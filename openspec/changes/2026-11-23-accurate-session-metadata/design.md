# Design

## Context

`SessionStore.list_sessions()` queries `sessions` and, for each row, the ordered `session_turns` joined to `session_meta` for category. It previously built a `non_audit` list excluding user turns starting with `audit: ` and assistant turns with `category == 'audit'`, then used that list for `preview` and `count`. As a result, an audit-only session (user `audit: what is the latest action?` + assistant `category='audit'`) returned `preview=''`, `count=0`, while `GET /sessions/{id}/history` returned both turns. `ChatPanel.vue:32` renders `{{ s.count }} messages` and `{{ s.preview }}` directly, so the wrong payload was the whole bug. `chat.py:45` carried a comment documenting the old exclusion.

## Goals / Non-Goals

**Goals:** History metadata matches the thread shown on open; audit exchanges are counted and previewed like any other turn; normal sessions are unchanged.

**Non-goals:** Changing chat storage, TTL, audit logging, the audit trail, the delete flow, UI layout/wording, or which sessions appear in the list.

## Decisions

- **Metadata source:** use the full ordered `turns` list. `count = len(turns)`; `preview` = first user turn's content truncated to 80 chars. Rationale: these are exactly the bubbles `session_history` returns, so the row and the opened thread agree. Alternative (keep filtering but add a separate "audit messages" label) rejected: more code and the user asked for an accurate count, not a new vocabulary.
- **No UI change:** `ChatPanel.vue` already binds `s.count`/`s.preview`; correcting the API payload fixes desktop and mobile history rails and the search filter at once.
- **Contract cleanup:** rename/rewrite `test_list_sessions_excludes_audit_and_shows_expired` to assert `count == 2` / `preview == 'audit: secret'` for the audit session and `count == 1` / `preview == 'old'` for the normal one, while still asserting both rows appear (expired sessions remain listed). Fix the `chat.py` comment so it no longer claims audit turns are excluded.
- **Unchanged:** owner-only account gating in `chat.py`, session ordering/limit, read-only `list_sessions` (no `last_active` touch), and all delete/audit behaviour.

## Risks / Trade-offs

- [Risk] Existing test encoded the old behaviour → Mitigation: rewritten test is the real-store proof (it writes an audit exchange into `SessionStore(":memory:")` and calls `list_sessions()`); full suite must stay green.
- [Risk] Audit rows now show a non-empty preview in a shared inbox → accepted: accurate metadata is the requested behaviour, and the `audit: ` prefix makes the nature of the conversation explicit.
- [Trade-off] "Messages" still counts turns (user + assistant), matching today's display (a one-exchange session shows 2).

## Migration Plan

1. Update `list_sessions()` and its docstring; fix the `chat.py` comment.
2. Rewrite the affected pytest and run the full suite.
3. `docker compose up -d --build api ui`; Playwright route-stub check of the rendered count/preview and the opened thread at 390×844 and 1200×900.
4. Rollback: restore the `non_audit` filter, its docstring/comment and the old test — no data migration.
