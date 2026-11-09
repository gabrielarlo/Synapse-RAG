# Design

## Context

Current inputs are inline `<input>`/`<select>` with divergent tokens: Chat composer `textarea` (`rounded-full px-4 py-2.5`, `disabled:` states) vs. form pages (`rounded-lg px-3 py-2`, no disabled states). No shared input component exists (`ui/src/components/` has only `ChatPanel.vue`, `ChatBox.vue`). Constraints: Vue 3.4 composition API (`defineModel` available), one view per resource, all API calls through `src/api.js`, Tailwind tokens already in use (see `proposal.md`).

## Goals / Non-Goals

**Goals:** One reusable `input` for text/number/password/search sharing the Chat pill tokens; replace all inline form inputs; keep Enter-to-send composer and all `v-model`, validation, `aria-label`, and layout behavior identical.

**Non-Goals:** Redesigning buttons, labels, checkboxes, or file inputs (stay native per spec); changing the Chat `textarea` composer into an `input`; touching backend, RLS, or auth.

## Decisions

- **Component:** New `ui/src/components/BaseInput.vue` (composition API, `<script setup>`) using `defineModel` with a `set` handler for the `.number` modifier: `defineModel({ set: (v) => props.number ? Number(v) : v })` — this gives `v-model.number` coercion for free and matches `Audit.vue` usage (`typeof filters.limit === 'number'`). Passthrough attrs (`type`, `placeholder`, `aria-label`, `required`, `disabled`, `autocomplete`, `min`) forward to the native `<input>`. Base classes are the Chat string; caller layout (`flex-1`, `w-full`, `w-28`, `text-sm`, `mt-1`, `pr-8`) passes via `class` but MUST NOT include conflicting radius/padding (`rounded-lg`, `px-3 py-2`) — base wins, caller strips conflicts. Rationale: single source of truth. Alternative (`modelValue`+`update:modelValue` manual cast) rejected: more code, still needs modifier plumbing.
- **Types:** `type="number"` keeps native number semantics; caller uses `.number` modifier as today (`Audit.vue` limit). File inputs stay native (complex `file:` styling) and checkboxes stay native (`accent-indigo-600`); they are out of scope in the spec. Alternative (a file wrapper) deferred to Non-Goals.
- **Selects:** Keep native `<select>`; align only the border/focus/disabled tokens. Form selects (`Staff.vue`, `Documents.vue` account) switch `rounded-lg px-3 py-2` → `rounded-full` pill; compact selects (Chat scope in `ChatPanel.vue`/`ChatBox.vue`, already `rounded-full px-3 py-1.5 text-xs disabled:`) keep their compact padding — do NOT force `px-4 py-2.5` on dense headers. Rationale: avoids regressing header layout. Alternative (full `BaseSelect` component) considered, deferred.
- **Search with trailing button:** `ChatPanel.vue` history search keeps `pr-8` and its clear-button alignment by passing `pr-8` through `class`; BaseInput does not hard-force `px-4`. Rationale: pill tokens + extra padding merge cleanly if base doesn't override `pr`.
- **Chat textarea:** Left as `textarea` in `ChatPanel.vue`/`ChatBox.vue`; Enter handler and `rows="1"` untouched. Only the history search input in `ChatPanel.vue` migrates to `BaseInput`. Rationale: textarea ≠ input; avoids breaking send behavior. Sharing its pill tokens is the visual contract.

## Risks / Trade-offs

- [Risk] `rounded-full` pill on dense `w-full` forms changes expected radius → Mitigation: deterministic check — computed `border-radius: 9999px` on Login/Audit/Staff inputs via Playwright before done.
- [Risk] `aria-label`/attrs lost if component doesn't forward `$attrs` → Mitigation: assert `aria-label` and `required` present per spec scenario; grep gate for remaining `rounded-lg` form inputs.
- [Risk] `v-model.number` coercion breaks if component emits strings → Mitigation: `defineModel` `set` handler above; verify `typeof filters.limit === 'number'` and numeric API param in Audit.
- [Trade-off] Single size (no `sm`/`md` variants) → dense Audit filters keep `text-sm` passthrough; if cramped, add size variants as follow-up.

## Migration Plan

1. Add `BaseInput.vue`, migrate Login, Accounts, Audit, Staff, `ChatPanel` search; align `Staff`/`Documents` selects (leave `ChatPanel`/`ChatBox` scope selects compact, token-check only).
2. `npm run dev` hot-reload check, then `docker compose up -d --build ui` and Playwright verification per repo gate.
3. Rollback: revert component file + per-view `<input>` restoration (classes only, no data migration).
