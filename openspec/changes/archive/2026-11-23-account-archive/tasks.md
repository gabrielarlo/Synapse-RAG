# Tasks

## 1. Data layer and migration

- [x] 1.1 Add `infra/migrations/007_account_archive.sql` with only `ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;` — no RLS policy changes.
- [x] 1.2 Apply 007 to the running deployment DB before rebuilding `api`, using the override-aware command (the `db` service lives in `docker-compose.override.yml`, which also sets `DATABASE_HOST=db` for `api`): `docker compose run --rm -v ./infra:/infra -e MIGRATIONS_DIR=/infra/migrations -e DATABASE_HOST=db api python /infra/db_init.py`. Verify `information_schema.columns` contains `accounts.is_archived` and `schema_migrations` records `007_account_archive.sql`.
- [x] 1.3 Extend `InMemoryStore` with `archived: set[str]`, `archive_account(id, archived)` and `is_archived(id)`; `list_accounts` returns `is_archived` and hides archived accounts for non-admin scope; `list_documents`, `get_document`, `document_content`, `search` and `claim_job` skip archived-account documents. Verify active rows unchanged.
- [x] 1.4 Extend `PostgresStore` with `archive_account(id, archived)` (with `_is_uuid` guard) and `is_archived(id)`; `list_accounts` selects `is_archived` and hides archived accounts for staff; add the `NOT EXISTS (SELECT 1 FROM accounts ...)` archived predicate to the same five reads. Verify unknown/malformed ids return False/None and both stores agree.

## 2. Authorization and API

- [x] 2.1 Add `POST /api/accounts/{id}/archive` and `/unarchive`, `admin_only`, 404 for unknown ids, idempotent (event recorded only on a real state change), audit events `account_archive` / `account_unarchive`. Verify staff gets 403 with no state change.
- [x] 2.2 Add archived rejection to `deps.resolve_scope` (403 `account archived`) for chat/document/session routes, and the same guard in `external.py` right after credential validation. Verify both paths refuse archived accounts; active accounts unaffected.
- [x] 2.3 Add `tests/test_account_archive.py` covering: admin success + staff 403; unknown id 404; idempotence and audit-event content/count; persisted flag via GET accounts (admin sees badge flag, staff list excludes archived); chat 403 and external FAQ 403; cascade with documents/chunks/jobs hidden from all five store reads and restored after unarchive; other accounts unaffected; active-account behavior unchanged. Full `pytest tests/ -q` green.

## 3. UI

- [x] 3.1 Add `api.archiveAccount(id)` and `api.unarchiveAccount(id)` in `ui/src/api.js`.
- [x] 3.2 In `Accounts.vue`, gate the action cell with `v-if="currentRole() === 'admin'"` (staff keep `—`); active rows get a 44×44 archive icon, archived rows an `Archived` badge plus a 44×44 restore icon; `aria-label`/`title` name the account, no raw UUIDs. Verify presence per role and row state.
- [x] 3.3 Add native `<dialog>` confirmation naming the exact account and stating documents become unavailable until unarchived; autofocused Cancel makes no request (assert via intercepted network, not only row state); danger-styled confirm calls the endpoint and reloads. Unarchive runs immediately with a status message. Verify cancel/confirm and success/error paths.

## 4. Gates

- [x] 4.1 `docker compose config` valid; `docker compose up -d --build api ui` and both containers Up; migration applied before the rebuilt `api` starts selecting `is_archived`.
- [x] 4.2 Playwright at 390×844 and 1200×900 against the rebuilt UI: `scrollWidth === clientWidth`; admin archive button renders and opens the dialog naming the account; Cancel makes no API request and leaves the row unchanged; confirm archives, shows the badge and removes the archive button; unarchive restores it; a staff session shows no archive control.
