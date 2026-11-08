# Design

## Context

Greenfield repo: no code, no specs. Constraints from the request: Docker Compose for everything except Ollama and PGSQL (external); `.env`-driven config; FastAPI + JWT; TailAdmin community (Vue3 + Tailwind); SQLite FTS5 for session memory; PGSQL + pgvector for vectors and tenant/account data with RLS; Ollama for generation, embeddings, and decision/triage. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Tenant-isolated RAG with one retrieval path gated by RLS for both internal and external callers.
- Small operable surface: `api/`, `ui/`, `worker/`, `infra/` (compose + `.env.example`).
- Ollama-backed triage → retrieval → generation pipeline with 30-min session memory and admin audit shortcut.

**Non-Goals:**

- TailAdmin Pro components, multi-model orchestration, per-department bots, full chat persistence beyond the 30-min window, document versioning UI.

## Decisions

- **Compose excludes Ollama/PGSQL; API connects via `OLLAMA_URL` / `DATABASE_URL`.** Rationale: request mandates external Ollama/PGSQL; keeps images small and avoids double-running stateful services. Alternative (bundle all) rejected — contradicts the brief.
- **Single FastAPI service + background worker for ingestion.** Rationale: uploads must return fast while chunk/embed/store runs async; one API keeps JWT + RLS logic in one place. Alternative (sync ingestion) rejected — embedding latency would time out uploads.
- **PGSQL RLS as the isolation primitive, not app-level filtering alone.** Rationale: both internal JWT and external key/secret paths share one enforcement point. Every scoped request carries an explicit `account_id`; the API verifies membership (admins bypass via a separate policy) then issues `SET LOCAL app.current_account` for exactly that one account. Internal retrieval matches that account plus `internal`; external FAQ matches only the credential-bound account, never `internal`. Alternative (app-only checks) rejected — two call paths would drift.
- **SQLite FTS5 for session memory, kept per explicit stack mandate.** Rationale: request requires FTS5; sessions bind at creation to one `(user, account_id)` pair and never cross accounts. `last_active` updates only on inbound user messages after the TTL check; `now - last_active > 30min` wipes context and sets the expiry notice. External FAQ is stateless (no sessions). Alternative (plain table) considered but rejected — stack explicitly mandates FTS5.
- **Ollama decision model as a typed triage step (`{category, escalate, department}`) before retrieval.** Rationale: explicit escalation/department routing the request demands; JSON-constrained output keeps it parseable. Internal processing order is fixed: authenticate → authorize → `audit: ` prefix check → triage → RLS retrieval → generation. `audit: ` short-circuits triage/retrieval on the internal admin path only; externals treat `audit: ` as literal text. Alternative (single LLM call) rejected — mixes routing with grounding.
- **Ingestion via PG-backed job table polled by the worker (no broker).** Rationale: compose ships only api/ui/worker with external PGSQL, so the queue lives in PGSQL (`ingestion_jobs`: pending/claimed/ready/failed); upload inserts and returns a job id immediately. Alternative (external broker) rejected — extra service for v1; alternative (in-API background tasks) rejected — loses retry/visibility the worker gives.
- **Audit questions via a fixed v1 intent allowlist, parameterized only.** Rationale: blocks NL→SQL injection; v1 intents: uploads/day, uploading users/day, questions per account/day, escalations per department/day, logins/day; anything else is refused with the supported list. Alternative (freeform NL→SQL) rejected — unsafe.
- **Rate limits on login/token and external FAQ (per IP / per key, 429 + retry hint).** Rationale: both are brute-forceable secrets endpoints.
- **External FAQ auth = key id + secret hash (bcrypt/argon2), full secret shown once.** Rationale: standard pattern, revocable/rotatable per account. Alternative (JWT for externals) rejected — accounts are not users with logins.
- **TailAdmin community Vue3 + Tailwind served as static build behind Compose `ui` service.** Rationale: exactly what was requested; admin/staff/account/document/audit screens map 1:1 to API resources.

## Risks / Trade-offs

- [Ollama model latency/availability] → Mitigation: startup health check, per-call timeouts, ingestion retries; document `failed` state.
- [RLS misconfiguration leaks tenants] → Mitigation: per-request `SET LOCAL` role/scope, integration test asserting cross-account exclusion on both internal and external paths.
- [SQLite FTS5 concurrency under workers] → Mitigation: WAL mode, single-writer discipline, sessions are small/ephemeral.
- [Decision-model output drift] → Mitigation: strict JSON schema + fallback (treat unparseable triage as non-escalated general query, logged).
- [`audit: ` natural-language → event aggregation] → Mitigation: fixed v1 intent allowlist (uploads/day, uploading users/day, questions per account/day, escalations per department/day, logins/day), parameterized queries only, refuse anything outside with the supported list.

## Migration Plan

Greenfield: `docker compose up --build` with `.env` from `.env.example`; run PGSQL migrations (extensions, tables, RLS policies); pull Ollama models; seed first admin. No rollback beyond `compose down` + migration down scripts.

## Open Questions

- Exact Ollama model ids (generation/embedding/decision) — pinned in `.env.example` at implementation time.
- Department taxonomy values — seeded as config, admin-editable later.
