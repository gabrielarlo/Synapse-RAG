-- 006_user_active.sql — deactivated users keep their data but lose all access.
-- Applied after 005_document_updated_at.sql, in filename order.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
