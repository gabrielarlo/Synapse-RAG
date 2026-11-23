# Proposal

## Why

Accounts can be created but never retired. Archiving is the reversible way to take a tenant out of service without deleting its documents, assignments, credentials or audit history. A bare icon with no handler is a false affordance; the action must genuinely change retrieval scope and be restricted to admins.

## What Changes

- Add `accounts.is_archived BOOLEAN NOT NULL DEFAULT FALSE` via ordered migration `007_account_archive.sql` (column only — existing RLS policies are untouched).
- Mirror the flag in `InMemoryStore` and `PostgresStore`; filter archived accounts out of `search`, `list_documents`, `get_document`, `document_content` and `claim_job` in both stores. `list_accounts` returns `is_archived` to admins; staff see only active accounts.
- Add admin-only `POST /api/accounts/{id}/archive` and `POST /api/accounts/{id}/unarchive`: 404 for unknown ids, idempotent, audit-logged only on a real state change. `resolve_scope` rejects archived accounts with 403 `account archived` for chat and document routes, and `external.py` adds the same guard because it builds its scope directly from the credential.
- Replace the placeholder icon in `ui/src/views/Accounts.vue` with a working action: per-row archive icon on active rows, `Archived` badge plus unarchive icon on archived rows, native confirmation dialog naming the account and consequence with danger-styled confirm and autofocused Cancel.
- Apply migration 007 to the running deployment DB before rebuilding `api` (compose does not apply SQL automatically).
- Scope-matched tests: render/click, confirm/cancel, admin-only authorization, persisted real effect, and cascade to documents/chunks/jobs under the account.

No **BREAKING** changes: existing accounts default to active and no response field is removed.

## Capabilities

### New Capabilities

- `account-archive`: reversible admin-only account retirement that excludes the account's documents from retrieval while preserving all data.

### Modified Capabilities

- None.

## Impact

- Affected code: `infra/migrations/007_account_archive.sql`, `api/app/store.py`, `api/app/db.py`, `api/app/deps.py`, `api/app/routers/accounts.py`, `ui/src/api.js`, `ui/src/views/Accounts.vue`, `tests/test_account_archive.py`, `openspec/specs/account-archive/spec.md`.
- Risk: a missed store read would expose archived documents — mitigated by enumerating all five reads in tests and asserting active-account behavior is unchanged.
- Gate: full pytest, `docker compose config`, migration applied, rebuild `api` + `ui`, Playwright at 390×844 and 1200×900.
