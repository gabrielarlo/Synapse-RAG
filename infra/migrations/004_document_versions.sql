-- 004_document_versions.sql — document replacement/versioning + decision-model category.
-- version increments on every accepted replace; category is tagged by the worker
-- (decision model) after ingestion and stays NULL until then.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS category TEXT;
