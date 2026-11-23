# Tasks

## 1. Backend

- [x] 1.1 Add `SessionStore.delete_session()` deleting `session_meta` → `session_turns` → `sessions` under the lock — verify with a store-level test that no rows remain for the sid.
- [x] 1.2 Add `DELETE /api/chat/sessions/{id}` with 404/403/account-membership checks matching the history endpoint and a `store.log` audit line — verify pytest 401/403/404/200 and an audit event for the session.

## 2. UI

- [x] 2.1 Add `api.deleteSession(id)` to `ui/src/api.js`.
- [x] 2.2 Add a trash button per history row in `ChatPanel.vue` (not on Live chat), tag both Live chat and session rows with `data-session-open`, scope `onListKey`, and add the danger-styled confirmation dialog naming the conversation — verify Playwright confirmation naming, Cancel, Delete, 44×44 target, no UUID, and arrow keys never landing on the trash button.
- [x] 2.3 Remove the deleted row on success and call `newSession()` when the deleted sid is live or being viewed; keep the row and show an error on failure — verify both Playwright paths.

## 3. Gates

- [x] 3.1 Run `.venv/bin/python -m pytest tests/ -q` green with the new cleanup/authorization test; `docker compose config` valid.
- [x] 3.2 `docker compose up -d --build api ui` and assert both containers Up.
- [x] 3.3 Playwright at 390×844 and 1200×900: `scrollWidth === clientWidth`, delete flow and keyboard navigation as above.
