-- 001_init.sql — Synapse-RAG base schema.
-- Applied in order on the EXTERNAL PGSQL. Requires the `vector` (pgvector) extension.
-- NOTE: chunks.embedding dim (768) must match EMBED_DIM / OLLAMA_EMBED_MODEL output.
-- Per-request scope (set by the API/worker on every transaction):
--   SET LOCAL app.current_account = '<account uuid>';  -- exactly one account
--   SET LOCAL app.caller = 'internal' | 'external';    -- internal sees +internal docs
--   SET LOCAL app.is_admin = '1' | '0';                -- admin bypass
-- PROD NOTE: connect as a NON-superuser role (superusers bypass RLS entirely).
-- FORCE ROW LEVEL SECURITY keeps even table owners gated.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Tenants ---------------------------------------------------------------
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'staff')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE staff_accounts (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, account_id)
);

-- Documents: exactly one scope — an account OR internal -----------------
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  is_internal BOOLEAN NOT NULL DEFAULT FALSE,
  filename TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'ready', 'failed')),
  error TEXT,
  uploaded_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((account_id IS NULL) = is_internal)
);

-- Chunks carry denormalized scope so RLS needs no join ------------------
CREATE TABLE chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  is_internal BOOLEAN NOT NULL DEFAULT FALSE,
  ord INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(768) NOT NULL
);

-- PG-backed ingestion queue (no broker) ---------------------------------
CREATE TABLE ingestion_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
  is_internal BOOLEAN NOT NULL DEFAULT FALSE,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'claimed', 'ready', 'failed')),
  attempts INT NOT NULL DEFAULT 0,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- External per-account credentials (secret stored hashed) ---------------
CREATE TABLE api_credentials (
  key_id TEXT PRIMARY KEY,
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  secret_hash TEXT NOT NULL,
  revoked BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit trail (admin-read, anybody-authenticated-can-append) ------------
CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
  detail TEXT
);
CREATE INDEX ON audit_events (action, ts);

-- Row-level security ----------------------------------------------------
-- Internal callers: own account + internal docs. External: own account only.
-- Admins bypass via app.is_admin but still pass an explicit account scope.
-- FORCE: even the table owner is gated, so an unset scope reads zero rows.
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
CREATE POLICY documents_tenant ON documents FOR ALL USING (
  current_setting('app.is_admin', true) = '1'
  OR account_id::TEXT = current_setting('app.current_account', true)
  OR (is_internal AND current_setting('app.caller', true) = 'internal'
      AND current_setting('app.current_account', true) <> '')
);

ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY chunks_tenant ON chunks FOR ALL USING (
  current_setting('app.is_admin', true) = '1'
  OR account_id::TEXT = current_setting('app.current_account', true)
  OR (is_internal AND current_setting('app.caller', true) = 'internal'
      AND current_setting('app.current_account', true) <> '')
);

ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY jobs_tenant ON ingestion_jobs FOR ALL USING (
  current_setting('app.is_admin', true) = '1'
  OR account_id::TEXT = current_setting('app.current_account', true)
);

ALTER TABLE api_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_credentials FORCE ROW LEVEL SECURITY;
-- Credential lookup runs admin-scoped (system); reads otherwise tenant-gated.
CREATE POLICY creds_tenant ON api_credentials FOR ALL USING (
  current_setting('app.is_admin', true) = '1'
  OR account_id::TEXT = current_setting('app.current_account', true)
);

ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_admin_read ON audit_events FOR SELECT USING (
  current_setting('app.is_admin', true) = '1'
);
CREATE POLICY audit_any_insert ON audit_events FOR INSERT WITH CHECK (true);
