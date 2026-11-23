# Proposal

## Why

Admins can create users, assign accounts and rotate credentials, but there is no way to revoke a user's access. Deleting a user would cascade away staff↔account assignments and orphan audit history. The platform needs a reversible "deactivated" state that immediately and completely blocks a user, controlled only by admins, without destroying data.

## What Changes

- Add `users.is_active BOOLEAN NOT NULL DEFAULT TRUE` via a new ordered migration (`006_user_active.sql`) and surface the flag on the `User` model in both stores and on `GET /api/auth/users`.
- Reject deactivated users at login, at refresh, and in the shared `authed` dependency so already-issued JWTs stop working on the very next request — not just at the next login.
- Add an admin-only `POST /api/auth/users/{user_id}/deactivate` endpoint that refuses to deactivate the caller (self), returns 404 for an unknown user, and writes an audit event.
- Add a deactivate icon button to each user row in `ui/src/views/Staff.vue`, hidden for the signed-in admin (self) and for already-inactive users. Activation opens a danger-styled confirmation dialog naming the exact user and consequence; the confirm action calls the new endpoint, then reloads the list.
- Show an `Inactive` badge on deactivated rows so their state is visible, and clear a deactivated user's local session on the specific `account deactivated` 403 so the UI redirects to login instead of looping on errors.
- Apply migration 006 to the deployment database **before** rebuilding `api` (via the documented `docker compose run ... db_init.py` flow), since compose does not apply SQL automatically.

No **BREAKING** changes: existing users default to active, and no endpoint or response field is removed.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `auth-identity`: adds a deactivated user state that blocks login, refresh and all authenticated requests, plus an admin-only deactivation action that cannot target the caller.

## Impact

- Affected code: `infra/migrations/006_user_active.sql`, `api/app/store.py`, `api/app/db.py`, `api/app/deps.py`, `api/app/routers/auth.py`, `ui/src/api.js`, `ui/src/views/Staff.vue`, `tests/test_auth.py`, `openspec/specs/auth-identity/spec.md`.
- Risk: the shared `authed` check is on every internal request path, so a mistake there locks out everyone — covered by tests asserting active users are unaffected. Deactivation has no API/UI reactivation path; re-enabling is a deliberate DB operation (see design trade-offs).
- Gate: full pytest suite, `docker compose config`, `docker compose up -d --build api ui`, and Playwright at 390×844 and 1200×900 with no horizontal scrolling.
