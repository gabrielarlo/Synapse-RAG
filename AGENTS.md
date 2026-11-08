# AGENTS.md — Synapse-RAG contributor guidelines

## Layout

- `api/` — FastAPI backend (`api/app/`: `main.py`, `config.py`, routers in `routers/`, `rag.py`, `sessions.py`, `store.py`, `audit_intents.py`, `ollama.py`). `api/requirements.txt`, `api/Dockerfile`.
- `worker/` — ingestion worker polling PG `ingestion_jobs` (`worker/worker.py`). `worker/requirements.txt`, `worker/Dockerfile`.
- `infra/migrations/` — numbered SQL migrations applied in order (`001_init.sql`, …).
- `ui/` — TailAdmin-community Vue 3 + Vite + Tailwind app (`VITE_API_URL` points at the API).
- `tests/` — pytest suite; hermetic by default (in-memory store, fake Ollama, temp SQLite). Live PG/Ollama tests are opt-in via env.
- `docker-compose.yml` at root; `.env` (gitignored) from `.env.example`.

## Config convention (.env-driven)

- Every environment-specific value comes from `.env`; `api/app/config.py` is the single loader and fails fast on missing required secrets (`JWT_SECRET`, `DATABASE_*`, `OLLAMA_URL`). The DSN is derived via `Settings.database_dsn` (keyword conninfo — never build URLs by hand; passwords may hold `@`/`:`).
- Never hardcode secrets, URLs, ports, or model names. Add new keys to `.env.example` with a comment.
- `OLLAMA_GEN_MODEL` / `OLLAMA_EMBED_MODEL` / `OLLAMA_DECISION_MODEL` default to locally available models; embedding dimension must match the `vector(N)` column.

## Request pipeline (do not reorder)

Internal: authenticate → authorize (role + `account_id` membership) → `audit: ` prefix check → decision-model triage → RLS-scoped retrieval → generation.
External `POST /ext/faq`: key/secret auth → stateless RAG on own account only (`audit: ` is literal text, `internal` docs excluded).

## Style

- Python: type hints on public functions, pydantic schemas at trust boundaries, raw parameterized SQL (no string-built queries).
- One RLS `SET LOCAL app.current_account` per scoped request; sessions bind `(user, account_id)`; `last_active` touches on inbound user messages only after the TTL check.
- Vue: composition API, one view per resource, all API calls through `src/api.js`.
- UI iteration: `npm run dev` in `ui/` for hot reload; after ANY `ui/` edit you MUST
  run `docker compose up -d --build ui` (compose serves a static build — edits
  are not picked up until rebuilt). Task is not done until the rebuilt `ui`
  container is Up.

## Gates (run before done)

- `.venv/bin/python -m pytest tests/ -q` — full suite green.
- `docker compose config` — compose file valid.
- Any `ui/` edit → `docker compose up -d --build ui` + container Up (required, not optional).
- New endpoint or behavior → test asserting it, including the 401/403/422/429 cases.
