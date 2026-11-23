# Design

## Context

`accounts` is the tenant table; `documents`, `chunks`, `ingestion_jobs`, `staff_accounts`, `api_credentials` and `audit_events` reference it. All app data access funnels through `InMemoryStore` (hermetic tests) and `PostgresStore` (prod), so the two stores must mirror behavior. `deps.resolve_scope` is the authorization gate for explicit account scope in chat and document routes; `external.py` builds its scope directly from an API credential and never calls `resolve_scope`. `authed`/`admin_only` gate roles. The Accounts view is a list of rows with a placeholder `—` in the action slot, currently rendered for every role; `Documents.vue` holds the house native-`<dialog>` confirmation pattern with danger styling. `docker-compose.yml` declares no database, but `docker-compose.override.yml` defines a `db` service and sets `api.environment.DATABASE_HOST=db` (confirmed by `synapse-rag-db-1` running).

## Goals / Non-Goals

**Goals:** an admin can archive and unarchive any account from the Accounts page; archived accounts are visibly badged; the account's documents, chunks and pending jobs stop being retrievable/processed immediately for every caller including admins, and come back on unarchive; no data is destroyed; confirmation guards the destructive direction.

**Non-Goals:** hard delete, bulk archive, cascading to chat sessions or audit history, notifying tenants, self-service unarchive by staff, changing account assignments or credentials on archive.

## Decisions

- **State flag on the account only.** No duplicated `is_archived` on documents. The account is the single source of truth; cascade is a filter derived from it, so unarchive restores everything automatically and cannot leave documents permanently orphaned.
- **Store-level cascade, not new RLS policies.** Every retrieval, management and worker read already goes through `store.search`, `store.list_documents`, `store.get_document`, `store.document_content` and `store.claim_job`; adding an archived-account predicate to those methods in both stores gives identical behavior for admins, staff and external callers. RLS keeps its existing tenant-isolation role and is left untouched. This avoids the PostgreSQL trap where a restrictive policy with only `USING` is reused as `WITH CHECK` and would reject writes for an archived account. Risk accepted: a job already claimed just before archive may finish and write chunks, but those chunks are filtered from `search`, so they are invisible.
  - `InMemoryStore` keeps `archived: set[str]`; the five reads skip documents whose `account_id` is archived.
  - `PostgresStore` adds `AND NOT EXISTS (SELECT 1 FROM accounts a WHERE a.id = <table>.account_id AND a.is_archived)` to the same reads; internal documents (`account_id IS NULL`) are unaffected.
  - `list_accounts` returns `is_archived`; staff see only active accounts, admins see all with the flag (so the badge and unarchive action exist).
- **Two explicit endpoints.** `POST /api/accounts/{id}/archive` and `/unarchive`, both `admin_only`, both idempotent, 404 for unknown ids, writing `account_archive` / `account_unarchive` audit events. Idempotent means the flag is set to the target value and the endpoint always succeeds for an existing id; an event is recorded only when the state actually changes. Two verbs keep UI intent unambiguous.
- **Scope gates in both entry points.** `resolve_scope` rejects archived accounts with 403 `account archived` (chat, document routes, session history). `external.py` adds the same guard immediately after credential validation, since it builds `Scope` directly and never calls `resolve_scope`. Store-level filters are the data boundary; these gates are the user-facing refusal so callers do not get a 200 with an empty answer.
- **UI.** The action cell is admin-only (`v-if="currentRole() === 'admin'"`); staff keep the `—` placeholder. Active rows get a 44×44 archive icon, archived rows get an `Archived` badge plus a 44×44 restore icon, each with `aria-label`/`title` naming the account and no raw UUIDs. Archive opens a native `<dialog>` naming the exact account and stating its documents become unavailable until unarchived; Cancel is autofocused and makes no request; confirm uses `bg-red-600`. Unarchive is non-destructive and runs immediately with a status message. Both call `api.js` then `load()`.
- **Migration rollout.** Apply 007 to the running DB before rebuilding `api`. Use the override-aware command with no shell passthroughs, relying on `env_file: .env` for credentials and only overriding the host to the compose `db` service: `docker compose run --rm -v ./infra:/infra -e MIGRATIONS_DIR=/infra/migrations -e DATABASE_HOST=db api python /infra/db_init.py`. Verify `accounts.is_archived` in `information_schema.columns` and `007_account_archive.sql` in `schema_migrations`.

## Risks / Trade-offs

- [Risk] A missed store read shows archived documents → Mitigation: enumerate all five reads in tasks and assert archived invisibility for search, list, get, content and worker claim, plus visibility after unarchive.
- [Risk] Archived account still has a claimed ingestion job → Mitigation: in-flight completion may write chunks but `search` filters them; no new jobs are claimable while archived (documented trade-off).
- [Risk] Admin can archive an account they use → Mitigation: unarchive is available and confirmation names the consequence.
- [Trade-off] Archived accounts remain in the admin list (badged) rather than being filtered out → without a visible row there is no unarchive affordance; staff do not see them at all.

## Migration Plan

1. Add 007 (column only), extend both stores, apply to the running DB before rebuilding `api`.
2. Add endpoints, both scope gates and tests.
3. Add `api.js` methods, admin-gated button, badge and confirmation dialog in `Accounts.vue`.
4. Run pytest, `docker compose config`, rebuild `api`/`ui`, then Playwright at phone and desktop widths. Rollback: revert code, `DELETE FROM schema_migrations WHERE name='007_account_archive.sql'` and `ALTER TABLE accounts DROP COLUMN is_archived`.
