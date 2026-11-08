-- 002_display_name.sql — operator display name for users.
-- Applied after 001_init.sql, in filename order.
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;
