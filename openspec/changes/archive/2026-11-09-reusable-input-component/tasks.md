# Tasks

## 1. BaseInput component

- [x] 1.1 Create `BaseInput.vue` with Chat pill tokens, `defineModel({ set })` for `.number`, and attr passthrough — verify `npm run build` succeeds and Login username computed `border-radius` is `9999px`.
- [x] 1.2 Preserve number coercion and accessibility — verify Playwright on Audit asserts `typeof filters.limit === 'number'` and numeric API param, plus `aria-label`/`required`/disabled states present.
- [x] 1.3 Align selects with explicit ownership — Staff role, Documents account (`Documents.vue:8` rounded-lg→rounded-full pill), Chat scope (`ChatPanel.vue`/`ChatBox.vue` compact token-check only, keep `px-3 py-1.5 text-xs`) — verify Playwright visual check shows consistent border/focus/disabled tokens and grep gate finds zero `rounded-lg` form inputs/selects.

## 2. Page migration

- [x] 2.1 Migrate Login and Accounts inputs — verify Playwright submit flows still succeed with prior `v-model` values and `pr-8` search layout preserved in ChatPanel.
- [x] 2.2 Migrate Audit and Staff inputs — verify Playwright filters/creation bind correctly, including Audit numeric limit assertion.
- [x] 2.3 Migrate ChatPanel search input, leave composer — verify Playwright Enter sends and Shift+Enter inserts newline, composer `rows="1"` untouched.

## 3. Gates

- [x] 3.1 Run repo gates — verify `.venv/bin/python -m pytest tests/ -q` green, `docker compose config` valid, and `docker compose up -d --build ui` container Up with Playwright checks (border-radius, number type, Enter/Shift+Enter) for Login/Audit/Staff/Chat.
