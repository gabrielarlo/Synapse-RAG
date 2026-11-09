-- 005_document_updated_at.sql — track last content change per document.
-- Set on replace; uploads keep the creation timestamp as the first update.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
