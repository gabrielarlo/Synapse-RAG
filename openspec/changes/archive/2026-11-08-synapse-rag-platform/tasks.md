# Tasks

## 1. Foundation (AGENTS.md, config, compose)

- [x] 1.1 Write root AGENTS.md (layout, .env convention, style, gates) and verify it exists with all four sections
- [x] 1.2 Add `.env.example` + config loader (fail fast on missing secrets) and verify `docker compose config` succeeds with example values
- [x] 1.3 Add Docker Compose (api, ui, worker only; external Ollama/PGSQL via URLs) and verify `docker compose up --build -d` starts all three and health endpoint reports dependency status — verified: `compose config` ok, native boot serves `/health` ok (db+ollama true); `up/build` blocked: no docker daemon in this env

## 2. Identity (JWT, roles, tenant assignments)

- [x] 2.1 Implement login + JWT issue/refresh and verify valid login returns a token and expired token yields 401
- [x] 2.2 Implement admin/staff roles + account CRUD + staff↔account assignment endpoints with explicit per-request `account_id` scope resolution (membership check, admin bypass policy) and verify staff listing is limited to assigned accounts
- [x] 2.3 Add assignment enforcement + login rate-limit tests and verify unassigned-account access returns 403, missing `account_id` returns 422, and throttled login returns 429

## 3. Data layer (PGSQL RLS + SQLite memory)

- [x] 3.1 Write migrations (pgvector ext, accounts, staff_accounts, documents, chunks, api_credentials, audit_events + RLS policies) and verify `migrate up` applies cleanly on a fresh external PGSQL
- [x] 3.2 Wire per-request RLS scope (single resolved `account_id` via `SET LOCAL`; internal adds `internal`, external own-account only) and verify cross-account vector query returns zero foreign chunks and externals never see `internal`
- [x] 3.3 Implement SQLite FTS5 session store bound to `(user, account_id)` (touch `last_active` on user message only after TTL check, external FAQ stateless) and verify stale session returns answer plus expiry notice and cross-account session reuse returns 403

## 4. Documents and ingestion

- [x] 4.1 Implement authenticated upload creating a `pending` row in the PG `ingestion_jobs` table (account-or-internal scope, 422 when missing) and verify authorized upload returns a job id immediately while unauthorized yields 403
- [x] 4.2 Implement worker chunk + Ollama embed + pgvector store with ready/failed status and verify a fixture doc becomes similarity-retrievable

## 5. RAG answering (triage, retrieval, generation)

- [x] 5.1 Implement internal pipeline order (auth → authz → `audit: ` prefix check → Ollama decision triage with safe fallback) and verify escalation case logs an audit event and labels the answer
- [x] 5.2 Implement RLS-gated retrieval + generation for internal JWT path and verify account-A query never surfaces account-B chunks and `internal` docs stay internal-visible only
- [x] 5.3 Wire session memory into the answer path and verify follow-up within 30 min uses context while late message carries expiry notice

## 6. External FAQ API (key/secret)

- [x] 6.1 Implement key/secret issuance, rotation, revocation (hashed storage, once-only plaintext) and verify old secret fails after rotation
- [x] 6.2 Implement stateless external FAQ endpoint with key/secret auth + per-key rate limit + RLS (own-account only, `audit: ` treated as literal text) and verify valid pair gets scoped answer, invalid gets 401, throttled gets 429, cross-account and `internal` content withheld

## 7. Auditing and audit: questions

- [x] 7.1 Implement audit event logging (login, upload, ingest, question, escalation, credential ops) + admin-only trail endpoint and verify staff access returns 403
- [x] 7.2 Implement `audit: `-prefix routing (internal admin only, before triage, fixed v1 intent allowlist with parameterized queries, refuse-with-list otherwise; non-admin → 403; never touches vectors) and verify `audit: how many users do upload files today?` returns a dated count and an off-allowlist question is refused

## 8. UI (TailAdmin community Vue3 + Tailwind)

- [x] 8.1 Scaffold TailAdmin community screens (login, accounts, staff assignments, documents, chat, audit) and verify `docker compose up` serves the UI hitting the API — verified: `vite build` ok (91 modules, dist/ emitted), endpoints match backend contract; served-via-compose blocked: no docker daemon in this env
- [x] 8.2 End-to-end verification: seed admin, assign staff, upload doc, ask question, expire session, call external FAQ, ask audit question — verify each spec scenario passes — verified: `test_live_e2e` green on real PG+pgvector+Ollama (session expiry covered hermetically with TTL injection)
