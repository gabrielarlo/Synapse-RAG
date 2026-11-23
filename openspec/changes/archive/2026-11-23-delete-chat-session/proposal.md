# Proposal

## Why

The chat history rail lists past conversations but offers no way to remove them. Users accumulate stale sessions (the screenshot shows many "Celestine Blooms" / "Internal" rows), and there is no owner-scoped way to delete one. Session data lives in three SQLite tables with no FK cascade, so deletion must clean all of them explicitly and stay auditable.

## What Changes

- Add `DELETE /api/chat/sessions/{session_id}` with the same restriction as the history endpoint: unknown → 404, other user → 403, account membership required for account-scoped sessions. Log the deletion via the existing `store.log(...)` mechanism, as document deletion already does.
- Add `SessionStore.delete_session()` removing rows from `session_turns`, `session_meta` and `sessions` in that order (no FK cascade exists).
- Add `api.deleteSession(id)` to the UI client.
- Add a trash button to each history row in `ChatPanel.vue` (not to the Live chat row), with a danger-styled confirmation dialog naming the conversation and its consequence. Remove the row on success; clear live/viewing session state if the deleted session was active. Keep arrow-key navigation working by tagging both Live chat and session rows.
- Add a pytest asserting owner-only access (401/403/404/200) and that no rows remain in any of the three tables, including orphan metadata.
- No changes to documents, the audit pipeline, or RLS; no **BREAKING** changes.

## Capabilities

### New Capabilities

- `chat-session-deletion`: owner-scoped, audited deletion of a persisted chat session with a confirming UI action.

### Modified Capabilities

- None

## Impact

- Affected code: `api/app/sessions.py`, `api/app/routers/chat.py`, `tests/test_sessions.py`, `ui/src/api.js`, `ui/src/components/ChatPanel.vue`, new OpenSpec change.
- No API contract is broken: existing list/history endpoints are unchanged; only a new DELETE route is added.
- Risk: deleting the active session must clear local session state or the next message would target a deleted id; extra per-row button must not break keyboard navigation or mobile layout. Both are covered by tests and Playwright checks.
