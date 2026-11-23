# Proposal

## Why

The UI was light-only: every page surface, card, dialog, input and badge used hardcoded slate/indigo light tokens, with no user-selectable theme and no way to follow the operating system's `prefers-color-scheme`. Tailwind's `darkMode` was unset, so it defaulted to `media` and could not be toggled. This change adds a persisted user theme preference with three modes — light, dark and system — where system follows OS changes live.

## What Changes

- Add a synchronous inline theme script in `ui/index.html` that resolves the stored theme preference (`light`/`dark`/`system`, defaulting to `system`) and applies `.dark`, `color-scheme` and `data-theme` to `<html>` before CSS paints — no flash of the wrong theme.
- Set `darkMode: 'class'` in `ui/tailwind.config.js` so the class can be toggled at runtime.
- Add one reusable `ThemeToggle.vue` (44×44, `shrink-0`, accessible) mounted in the app header and on the login card. The two are mutually exclusive, so no shared store is needed: the toggle reads the stored preference, cycles light → dark → system, persists `localStorage['theme']`, and follows OS changes live while in system mode.
- Add `dark:` companions to all light surfaces, text, borders, focus rings, scrollbars, native select chevron, and status/action badges across `index.css`, `App.vue`, all components and all views. The already-dark sidebar and indigo primary actions are unchanged.
- No backend, API, database or auth changes. No **BREAKING** changes.

## Capabilities

### New Capabilities

- `dark-mode`: user-toggleable light/dark/system theme preference with persistence, live system following, first-paint correctness, and readable contrast across all UI pages.

### Modified Capabilities

- None

## Impact

- Affected code: `ui/index.html`, `ui/tailwind.config.js`, `ui/src/index.css`, new `ui/src/components/ThemeToggle.vue`, `ui/src/App.vue`, `ui/src/components/{BaseInput,ChatPanel,ChatBox,A2UIRenderer}.vue`, `ui/src/views/{Login,Chat,Documents,Accounts,Staff,Audit}.vue`.
- No API or data behavior changes: every `v-model`, filter, dialog, Enter-to-send handler, `aria-*` attribute, and the mobile card/table split stay intact — only color tokens change.
- Risk: pastel badges can become unreadable in dark mode if only backgrounds are darkened; every badge therefore pairs a translucent dark background with a light `dark:text-*-300`. Native dialogs and scrollbars need `color-scheme` set on `<html>`. Follow the repo UI gate: `npm run build`, broadened grep gate, `docker compose up -d --build ui`, and Playwright at 390×844 and 1200×900 including a seeded-`localStorage` no-FOUC check.
