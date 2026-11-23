-- 007_account_archive.sql — reversible account retirement.
-- Archived accounts stay in place; the stores filter their documents,
-- chunks and jobs from retrieval until the account is unarchived.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;
