# Design — strict scope authorization

See proposal.md for motivation.

## Goals / Non-Goals

- One scope per request, enforced identically in both stores and the API.
- Non-goals: no DB/RLS migration; the PG `_tx` path maps internal scope to
  the nil-UUID `current_account` sentinel so existing RLS admits internal
  rows; no new API params (clients already send exactly
  one scope); external FAQ untouched.

## Decisions

- **Store layer flips, not the router.** `Scope` already carries exactly one
  `account_id` or the internal caller flag. InMemoryStore filters in Python;
  PostgresStore gets an explicit single-scope `WHERE` (`account_id=%s` for
  account scopes, `is_internal` for internal scope, unfiltered only for
  admin) instead of a new RLS migration — today the PG store has no SQL
  `WHERE`, so RLS alone leaks internal rows into account scope. And RLS's
  `current_account<>''` clause returns zero rows for internal scope
  (`account_id=None` → `current_account=''`), a live prod bug. Fix without
  a migration: in the non-admin PG path, set `current_account` to the nil
  UUID sentinel (`00000000-0000-0000-0000-000000000000`) for internal scope
  — non-empty so the internal clause passes, matching no real account so
  account rows stay hidden. `WHERE is_internal` then returns exactly the
  internal rows. RLS stays as backstop.
- **Management tightening lives in `_authorize`** (replace/delete) **and the
  view endpoint**: internal view is admin-only; account rules unchanged;
  upload path unchanged so staff can still create internal documents.

## Risks / Trade-offs

- Behavior change is breaking: account-scoped chats will abstain where they
  previously answered from internal docs. Accepted per the change's intent.
- `list_documents` for an account scope must not fall back to internal rows
  "because none exist locally" — strict filter even when empty.
