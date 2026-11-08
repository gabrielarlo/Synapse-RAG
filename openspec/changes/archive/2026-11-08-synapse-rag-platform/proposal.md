# Proposal

## Why

Teams need a self-hosted, multi-tenant RAG service where staff upload account-scoped documents and both internal users and external accounts get grounded FAQ answers, with auditability for admins. No such foundation exists in this repo (greenfield), so we need the full platform slice: API, UI, vector store, memory, and access control.

## What Changes

- Scaffold repo foundation: `AGENTS.md` general guidelines, `.env`-driven configs, Docker Compose for all services except Ollama and PGSQL (which stay external), FastAPI backend, TailAdmin community (Vue3 + Tailwind) frontend.
- Multi-role identity: `admin` (all tenants) and `staff` (assigned to one or more accounts); multi-tenant account management with staff↔account many-to-many assignment; JWT authentication on FastAPI.
- Document ingestion: authenticated upload, chunk + embed via Ollama, store in PGVector; each document attached to exactly one account or marked `internal`.
- RAG answering: decision-model triage (category, escalation flag, department routing) via Ollama, retrieval gated by row-level security (internal and/or API paths), per-session temporary context memory expiring 30 mins after latest interaction with user-visible notice.
- External FAQ API: per-account API key + secret, public FAQ endpoint authenticating via key/secret, RLS-scoped retrieval.
- Auditing: admin-only audit surface; questions prefixed with `audit: ` (e.g. `audit: how many users do upload files today?`) answered from audit/event data, never from document vectors.

## Capabilities

### New Capabilities

- `platform-foundation`: dockerization (excluding Ollama/PGSQL), `.env` config convention, `AGENTS.md` guidelines, service layout (API/UI/worker).
- `auth-identity`: JWT auth, admin/staff roles, tenant/account CRUD, staff↔account assignments.
- `document-ingestion`: document upload, chunking/embedding via Ollama, PGVector storage with account-or-internal scoping.
- `rag-answering`: decision-model triage + escalation/department routing, RLS-gated retrieval, 30-min session memory with expiry notice.
- `external-faq-api`: per-account API key/secret issuance and rotation, external FAQ endpoint with key/secret auth and RLS enforcement.
- `auditing`: admin-only audit trail and `audit: `-prefixed question handling.

### Modified Capabilities

- None (greenfield, no existing specs).

## Impact

- New services: FastAPI backend, TailAdmin Vue3 frontend, ingestion worker, PGSQL (external, pgvector + RLS), Ollama (external, generation/embeddings/decision), SQLite FTS5 for session memory.
- New APIs: internal JWT REST + external key/secret FAQ endpoint; new RLS policies on all tenant-scoped tables.
- Dependencies: `pgvector` extension, Ollama models (generation, embedding, decision), TailAdmin community template.
