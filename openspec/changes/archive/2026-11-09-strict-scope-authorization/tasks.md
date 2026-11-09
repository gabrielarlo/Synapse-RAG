# Tasks — strict scope authorization

## 1. Store layer

- [x] 1.1 InMemoryStore `list_documents`/`search`: single scope — account scope excludes internal, internal scope excludes account docs; **no admin bypass** (selection always wins; admin bypass survives only in management authorization)
- [x] 1.2 PostgresStore `list_documents`/`search`: explicit single-scope SQL `WHERE` (`account_id=%s` / `is_internal`); internal scope sets `current_account` to the nil-UUID sentinel so RLS admits internal rows (fixes prod internal-scope-empty bug); no migration, RLS as backstop

## 2. API

- [x] 2.1 `documents._authorize`: internal replace/delete admin-only; upload unchanged (staff may create internal docs)
- [x] 2.2 `documents.view`: internal documents admin-only (staff 403); account membership rule unchanged
- [x] 2.3 `GET /api/chat/sessions/{id}/history`: owner-only thread restore (account-membership gated for account sessions); UI refetches and rebuilds bubbles on reload

## 3. Verification

- [x] 3.1 Hermetic test updates (existing expectations flipped): `test_rag_isolation.py` merged-scope assertions → strict single scope; `test_document_manage.py` staff-replace-own-internal 200 → 403, staff view internal → 403; new: account search/list exclude internal, internal search/list exclude account docs, staff internal upload 200
- [x] 3.1b Live e2e `test_live_e2e.py`: account search assertions no longer expect internal rows; internal `list_documents` and `search` under `account_id=None` return internal rows in Postgres (covers the `WHERE` + sentinel)
- [x] 3.2 Full pytest suite green (74 passed); `docker compose config`; api+ui rebuilt and Up
- [x] 3.3 Live smoke + Playwright: Hugo chat no longer cites internal PDFs; reload restores scope, session badge, and message thread

## 4. Specs

- [x] 4.1 Delta specs in this change; sync on archive
