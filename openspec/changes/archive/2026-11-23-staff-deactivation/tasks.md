# Tasks

## 1. Active state in the data layer

- [x] 1.1 Add `infra/migrations/006_user_active.sql` with `ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;` — verify `infra/db_init.py` applies it in order on a fresh schema and that existing rows stay active.
- [x] 1.1b Apply the migration to the **running deployment DB before rebuilding/restarting `api`**, using the `start.sh` pattern with `DATABASE_HOST=db` from `docker-compose.override.yml` (forwarding `.env`'s `host.docker.internal` would migrate the wrong database): `docker compose run --rm -v ./infra:/infra -e MIGRATIONS_DIR=/infra/migrations -e DATABASE_HOST=db -e DATABASE_PORT=5432 -e DATABASE_NAME -e DATABASE_USER -e DATABASE_PASSWORD api python /infra/db_init.py`; verify `006_user_active.sql` is recorded in `schema_migrations` and `information_schema.columns` contains `users.is_active`. Without this the rebuilt API selects a missing column and all auth requests 500.
- [x] 1.2 Add `is_active: bool = True` to `User` in `api/app/store.py`; make `InMemoryStore.create_user` keep the default — verify existing store tests stay green.
- [x] 1.3 Add `deactivate_user(user_id) -> bool` to `InMemoryStore` and `PostgresStore` and include `is_active` in every user SELECT in `api/app/db.py` — verify a missing id returns False and no caller of `User(...)` breaks.

## 2. Enforcement and admin endpoint

- [x] 2.1 Reject inactive users in `deps.authed()` after the store lookup with 403 `account deactivated` — verify active admin/staff still pass and a token issued before deactivation is rejected on the next request.
- [x] 2.2 Reject inactive users in `auth.login` and `auth.refresh` with the same 403 — verify deactivated credentials cannot get new tokens.
- [x] 2.3 Add `POST /api/auth/users/{user_id}/deactivate` (admin_only): 404 for unknown id, 422 when target is the caller, idempotent, audit-logged — verify staff gets 403 and an admin cannot deactivate themselves.
- [x] 2.3b Reject malformed user ids in `PostgresStore.deactivate_user` with the existing `_is_uuid` guard so the endpoint returns 404 instead of a psycopg UUID-cast 500 — verify with a no-DB unit test and the live API.
- [x] 2.4 Return `is_active` from `GET /api/auth/users` (not `/me`, which an inactive user can never reach) — verify the flag comes from the store, not the token.
- [x] 2.5 Add tests in `tests/test_auth.py` for all of the above, including "deactivation revokes an already-issued token" — verify `.venv/bin/python -m pytest tests/ -q` is green.

## 3. Staff UI

- [x] 3.1 Extract the JWT decode in `api.js` into one payload helper, expose `currentUsername()` alongside `currentRole()`, add `api.deactivateUser(userId)`, and handle only the 403 with detail `account deactivated` in the response interceptor by clearing both tokens and redirecting to `/login` (no blanket 403 logout) — verify `currentRole()` behavior is unchanged, staff 403s do not log out, and a deactivated token clears the session.
- [x] 3.2 In `Staff.vue`, add the per-row deactivate icon button (admin only, not self, not already inactive, ≥44px, danger styling, `aria-label`/`title`) plus an `Inactive` badge — verify the button is absent on your own row and on inactive rows.
- [x] 3.3 Add the native `<dialog>` confirmation naming the user and consequence with a danger confirm button and autofocused Cancel; call the endpoint, show success/error status and reload — verify cancel makes no request and confirm flips the row to inactive.
- [x] 3.4 Run `npm run build`, `docker compose config`, `docker compose up -d --build api ui` and assert both containers are Up.

## 4. Gates

- [x] 4.1 Full pytest suite green.
- [x] 4.2 Playwright at 390×844 and 1200×900 against the rebuilt UI: `scrollWidth === clientWidth`, button present only for other users, confirmation text/cancel/confirm behavior, inactive badge after deactivation.
