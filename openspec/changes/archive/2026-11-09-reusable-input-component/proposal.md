# Proposal

## Why

Input styles are duplicated and have drifted across 8 UI files with no shared component: the Chat composer uses a pill shape (`rounded-full px-4 py-2.5` with `disabled:` styles) while form pages use `rounded-lg px-3 py-2` without disabled states. Task: "make the input design consistent in all pages. follow the design if inputs from chat page. make input component to make it reusable."

## What Changes

- Create a reusable Vue input component (e.g. `BaseInput.vue`) encapsulating the Chat input look: `border-slate-200`, `rounded-full`, `px-4 py-2.5`, `focus:border-indigo-500`, `disabled:bg-slate-50 disabled:text-slate-400`, with `v-model` + `.number` support, preserving Chat `textarea` behavior (`rows="1"`, Enter-to-send stays in composer).
- Replace inline `<input>` in `Accounts.vue`, `Audit.vue`, `Staff.vue`, `Login.vue` and the Chat search box (`ChatPanel.vue` history search) with the component via `v-model`. Chat search keeps `pr-8` for its clear button.
- Unify `select` and filter input tokens to the same border/focus/disabled tokens while preserving layout (`flex-1`, `w-28`, `text-sm`) and `aria-label` attributes. Compact Chat scope selects (`rounded-full px-3 py-1.5 text-xs`) keep compact padding — token alignment only.
- Checkboxes and file inputs stay native (out of scope). No API or data behavior change: same bindings, validation, disabled logic. No **BREAKING** changes.

## Capabilities

### New Capabilities

- `reusable-input`: Reusable input component API and consistent input visual language across pages.

### Modified Capabilities

- None

## Impact

- Affected code: new file in `ui/src/components/`, plus `ui/src/views/Login.vue`, `Accounts.vue`, `Audit.vue`, `Staff.vue`, `Documents.vue` (account select only), `ui/src/components/ChatPanel.vue`, `ChatBox.vue` (scope selects token-checked).
- No backend/API/database changes.
- Risk: type variants (text/number/password/search), `file:` styling, and a11y attributes must be preserved. Follow repo UI gate: `npm run dev` + `docker compose up -d --build ui` + Playwright checks (deterministic: computed `border-radius:9999px`, `typeof limit === 'number'`, Enter/Shift+Enter, grep gate for leftover `rounded-lg`).
