# Tasks

## 1. Backend

- [x] 1.1 Compute `list_sessions()` count from all persisted turns and preview from the first user turn, including audit exchanges; update the docstring — verify with a real `SessionStore(":memory:")` test that an audit session reports count 2 and preview `audit: secret`.
- [x] 1.2 Rewrite `test_list_sessions_excludes_audit_and_shows_expired` for the new contract (audit count 2/preview `audit: secret`, normal count 1/preview `old`, both rows still listed) and fix the stale `chat.py:45` comment.

## 2. Verification

- [x] 2.1 Run targeted and full `.venv/bin/python -m pytest tests/ -q` green with no other test regressions.
- [x] 2.2 `docker compose up -d --build api ui` and assert both containers Up.
- [x] 2.3 Playwright with `page.route` stubs for `**/api/chat/sessions**`, `**/api/chat/sessions/*/history` and `/api/accounts` plus a seeded `access_token`: assert the audit row renders "2 messages" and the `audit: secret` preview, opening it shows matching bubbles, normal rows unchanged, and `scrollWidth === clientWidth` at 390×844 and 1200×900.
