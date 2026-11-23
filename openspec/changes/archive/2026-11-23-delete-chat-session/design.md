# Design

## Context

Chat sessions are stored in SQLite via `SessionStore` (`sessions`, `session_turns` FTS5, `session_meta` keyed by turn rowid). There is no FK cascade or `PRAGMA foreign_keys`, so the existing TTL-expiry code deletes meta → turns explicitly and leaves the `sessions` row. `chat.py` already implements owner + account-membership checks for `GET /sessions/{id}/history` using `get_session()` and `resolve_scope()`. The history rail in `ChatPanel.vue` renders one full-width button per session plus a Live chat row; `onListKey` currently selects every button in the `<ul>`. `Documents.vue` has an established `<dialog>` + `showModal()` confirmation pattern with danger styling. `documents.py:212` logs destructive deletes with `store.log(actor=..., action="delete", account_id=..., detail=...)`.

## Goals / Non-Goals

**Goals:** One owner-scoped delete action per history row, audited, with a clear destructive confirmation, correct cleanup of all three tables, and no regression to keyboard navigation or mobile layout.

**Non-Goals:** Bulk delete, deleting the Live chat row itself, retention policies, changes to documents or the audit pipeline itself.

## Decisions

- **Store:** `delete_session(session_id)` deletes `session_meta` for that session's turn rowids, then `session_turns`, then `sessions`, under the existing lock, and commits. Rationale: mirrors the TTL-expiry order and avoids orphan rows; no cascade exists. A mid-delete failure could leave the shared connection's transaction open — pre-existing pattern, no new rollback logic.
- **Endpoint:** `DELETE /api/chat/sessions/{session_id}`, mirroring `session_history` exactly for 404 / 403 / account membership, then delete and `store.log(actor=user.username, action="delete", account_id=bound_account or None, detail=f"session {session_id}")`. Return `{"deleted": session_id}`. Rationale: same authorization contract as reading a session; destructive actions are audited like document deletion.
- **UI row:** each history `<li>` becomes `flex items-center gap-1`; the session button gets `flex-1 min-w-0` and `data-session-open`, and a `w-11 h-11 shrink-0` trash button is added with `data-delete-session` and an `aria-label` built from `sessionScope(s)` (human-readable account name or "Internal" — never a UUID). The Live chat button also gets `data-session-open` so it remains the first arrow-key stop. `onListKey` is scoped to `button[data-session-open]:not([disabled])` so the trash button is never a navigation stop.
- **Confirmation:** a `<dialog>` following `Documents.vue` — names the exact conversation and states that the conversation and its messages are permanently deleted; Cancel is neutral, Delete is danger-styled and visually distinct. `showModal()` opens it, focus is restored to the invoking button on close. Rationale: destructive actions must not fire from a bare icon click; extracting a shared confirm component would require refactoring three existing dialogs in `Documents.vue`, a larger unrelated diff.
- **Success handling:** clear any prior `error.value` before the request; remove the row from `historySessions`; if the deleted id is the live `sessionId` or the `viewingSid`, call the existing `newSession()` (clears live/viewing state, messages, draft and error and persists) instead of re-specifying cleanup. Failure keeps the row and sets `error.value`. The pre-request clear prevents a stale error from a previous failed delete surviving a later success.

## Risks / Trade-offs

- [Risk] Extra button breaks arrow-key navigation → Mitigation: `data-session-open` on both Live chat and session rows; Playwright asserts arrows reach Live chat and never the trash button.
- [Risk] Orphaned child rows fail silently → Mitigation: required pytest assertions on all three tables using turn ids captured before deletion.
- [Risk] Deleting the active session leaves a stale id → Mitigation: reuse `newSession()`.
- [Risk] Destructive action without confirmation → Mitigation: dialog above, danger styling, focus restore.
- [Trade-off] Deleting a viewed (non-live) session also clears the live session draft — accepted because `newSession()` is the single existing cleanup path.

## Migration Plan

1. Add store method and DELETE endpoint with audit log; add API client method.
2. Update `ChatPanel.vue` rows, keyboard selector and confirmation dialog.
3. Add pytest for authorization + child-row cleanup; run full suite.
4. `docker compose up -d --build api ui`; Playwright UI flow at 390×844 and 1200×900.
5. Rollback: remove the route/store method/API client and restore the original row markup — no data migration (a deleted session is intentionally unrecoverable).
