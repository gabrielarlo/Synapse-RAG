-- 008_api_tokens.sql — label + expiry + hard delete for API tokens.
-- Existing keys get a 90-day default from creation time.
ALTER TABLE api_credentials ADD COLUMN IF NOT EXISTS label TEXT;
ALTER TABLE api_credentials ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
-- backfill + default: existing rows → created_at + 90 days, new rows → now() + 90 days
UPDATE api_credentials SET expires_at = created_at + interval '90 days' WHERE expires_at IS NULL;
ALTER TABLE api_credentials ALTER COLUMN expires_at SET DEFAULT (now() + interval '90 days');
ALTER TABLE api_credentials ALTER COLUMN expires_at SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_api_credentials_expires ON api_credentials(expires_at);
