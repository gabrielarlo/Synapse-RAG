# Design

## Context

`User` is a dataclass in `api/app/store.py` shared by `InMemoryStore` (tests) and `PostgresStore` (`api/app/db.py`). Both stores select explicit columns, so adding a field requires touching each SELECT. Auth is stateless HS256 JWT (`sub` = username, `role`, `kind`); `deps.authed()` is the single dependency behind every internal route, including `admin_only()`. Login and refresh live in `routers/auth.py`. The Staff view is an admin-only page in practice (`GET /api/auth/users` is `admin_only`) that lists all users, with the current user among them. UI uses Vue 3 composition API, `api.js` as the single API surface, and native `<dialog>` confirmations with danger styling in `Documents.vue`.

## Goals / Non-Goals

**Goals:** an admin can deactivate any other user from the Staff page; deactivation takes effect on the next request even for an existing token; the caller cannot deactivate themselves; the action is explicit and confirmed; deactivated users are visibly marked.

**Non-Goals:** reactivation API/UI, hard delete, bulk deactivation, changing roles or account assignments on deactivation, an audit-viewer UI, and notifying the deactivated user.

## Decisions

- **State, not deletion:** add `is_active` with default `TRUE` so all existing rows stay active and no assignment or audit data is lost. Reactivation is intentionally out of scope: it is a deliberate DB operation (`UPDATE users SET is_active = TRUE ...`), which keeps the admin UI's destructive surface small. A danger-styled confirmation dialog mitigates accidental clicks. The store method is therefore `deactivate_user(id)` (no generic active setter), and `GET /api/auth/me` does not expose the flag — a deactivated user never reaches `/me` because `authed()` refuses first, and active users are always true. `GET /api/auth/users` does expose it, because the Staff badge needs it.
- **Enforcement in three places:** login and refresh reject inactive users with 403 `account deactivated`; `authed()` checks `user.is_active` after loading the user from the store, so every already-issued token stops working on its next use. Checking only login would leave valid tokens live for their full lifetime, which does not satisfy "deactivate". 403 (not 401) distinguishes a deliberate admin action from a bad credential; the response text is identical for all inactive users and does not reveal who deactivated them. The UI response interceptor gains a narrow branch for exactly this 403 detail that clears both tokens and redirects to `/login`; it must not be a blanket 403 handler, or staff hitting admin-only routes would be logged out.
- **Migration rollout:** `docker compose.yml` has no migration service and compose does not hot-apply SQL, so the new column must be applied to the deployment DB *before* the rebuilt `api` starts selecting it. Use the `start.sh` pattern with one correction for this checkout: `docker-compose.override.yml` sets `DATABASE_HOST=db` for `api`, so pass that value explicitly rather than forwarding `.env`'s `host.docker.internal`: `docker compose run --rm -v ./infra:/infra -e MIGRATIONS_DIR=/infra/migrations -e DATABASE_HOST=db -e DATABASE_PORT=5432 -e DATABASE_NAME -e DATABASE_USER -e DATABASE_PASSWORD api python /infra/db_init.py`, then verify `SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_active';` returns one row. Without this, every auth request 500s against a 001–005 database.
- **Endpoint shape:** `POST /api/auth/users/{user_id}/deactivate` with `admin_only` dependency. It resolves the target by id via a new store method, returns 404 for unknown ids, and returns 422 when `user_id == admin.id` — the same guard the UI applies by hiding the button for self, so the rule holds even for direct API calls. The endpoint writes `store.log(actor=admin.username, action="user_deactivate", detail=...)`. No request body: deactivation is unconditional and idempotent for an already-inactive user.
- **Self-identification in the UI:** add `currentUsername()` to `api.js` by extracting the existing JWT-decode body of `currentRole()` into one shared helper. `sub` is the signed username, so comparing it to `u.username` needs no extra `/me` request and cannot be spoofed from the UI.
- **Button and confirmation:** one icon button per row in the existing user list, rendered only when `currentRole() === 'admin'`, `u.username !== currentUsername()` and `u.is_active`. It is a 44×44 `shrink-0` control with `aria-label`/`title` naming the target, danger hover/focus colors, and an SVG "user-slash" icon. Clicking opens a native `<dialog>` matching `Documents.vue`: text names the exact username and states that access is revoked immediately, Cancel is autofocused, and the confirming button uses `bg-red-600` danger styling. On success the dialog closes, a status message is shown, and `load()` refreshes the list so the row flips to an `Inactive` badge with no button.
- **List response:** `GET /api/auth/users` gains `is_active` per user; the UI shows an `Inactive` badge next to the role when false. No UUID is displayed.

## Risks / Trade-offs

- [Risk] A bug in `authed()` locks out all users → Mitigation: the check is one line after an existing successful user lookup; tests assert active admin/staff still reach `/api/auth/me` and that a token issued before deactivation gets 403 afterwards.
- [Risk] Deactivation is not reversible through the product → Mitigation: explicit confirmation naming the user and consequence; documented DB reactivation; accepted as a non-goal.
- [Risk] Mobile row crowding with a new icon → Mitigation: `shrink-0` button, `min-w-0 truncate` on the name, Playwright check at 390×844 for `scrollWidth === clientWidth`.
- [Risk] Stale token payload vs store state → Mitigation: role still comes from the signed token as before, but active state is always read live from the store on each request.
- [Trade-off] 403 for deactivated accounts leaks "this account exists but is disabled" to someone with valid credentials for it — acceptable, since the caller already knows the credentials.

## Migration Plan

1. Add `006_user_active.sql` and extend the `User` model / both stores.
2. Add enforcement in `deps.py` and `auth.py`, then the admin endpoint and tests.
3. Add `api.js` helper + `deactivateUser`, then the button, dialog, badge and status message in `Staff.vue`.
4. Run pytest, `docker compose config`, rebuild `api` and `ui`, then Playwright at phone and desktop widths. Rollback: revert code and `DELETE FROM schema_migrations WHERE name='006_user_active.sql'` plus `ALTER TABLE users DROP COLUMN is_active`.
