# Design

## Context

The UI is a Vue 3.4 composition-API app using Tailwind 3.4.13 (not v4). `ui/tailwind.config.js` has no `darkMode` key, so Tailwind defaults to `media` (OS-only, not user-toggleable). All surfaces are light-only utilities — `bg-white`, `bg-slate-50/100`, `border-slate-100/200`, `text-slate-600/700/800`, plus pastel `indigo-50`/`amber-50`/`red-50`/`emerald-50`/`violet-50` badges and script-derived action tones in `Audit.vue`. The only already-dark region is the gradient sidebar in `App.vue`. `localStorage` is already used for `sidebar_collapsed` and `chat_session` with `try/catch` guards. Repo gate: any `ui/` edit requires `docker compose up -d --build ui` (compose serves a static build, no hot reload).

## Goals / Non-Goals

**Goals:** One accessible toggle that cycles the UI through light, dark and system; the choice survives reload; system follows OS changes live; no flash of the wrong theme on first paint; readable contrast on every page, including badges, dialogs, and mobile cards.

**Non-Goals:** Custom palettes, theme editor, backend/user-profile persistence, a settings view, and any layout/spacing/motion redesign.

## Decisions

- **Theme bootstrap:** a synchronous inline `<script>` in the `<head>` of `index.html`, placed after the viewport meta and before Vite's injected stylesheet/module script. It reads `localStorage['theme']` validated to `light`/`dark`/`system` (default `system`), computes effective dark as `mode === 'dark' || (mode === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)`, adds `.dark` to `document.documentElement`, sets `style.colorScheme` and `dataset.theme`. Rationale: `main.js` is a deferred module, so an import-time theme function would paint the light `bg-slate-100` body first (FOUC). Alternative rejected: a `theme.js` composable — extra file, module-timing dependency, and no benefit because the two toggle instances are mutually exclusive (`App.vue` header is `v-if="loggedIn"`; `Login.vue` only at `/login`).
- **Toggle component:** one `ThemeToggle.vue` whose `mode` ref is initialized from `localStorage['theme'] || 'system'` (validated), **never** from the `.dark` class — that class is identical for `dark` and `system` + OS-dark, so deriving mode from it would silently break the cycle and live following. `cycle()` advances light → dark → system, persists the choice and re-applies the DOM. A `matchMedia('(prefers-color-scheme: dark)')` `change` listener is added on mount and removed on unmount; it re-applies only when `mode === 'system'`, so explicit choices ignore OS changes. Each state has its own icon (sun/moon/monitor) and an `aria-label`/`title` naming current and next mode; `data-theme` on `<html>` exposes the mode for tests instead of binary `aria-pressed`. Exactly two mount points — `App.vue` header after the title, and `Login.vue` inside the `p-8` form column in a `flex justify-end` row. Both instances are 44×44 with `shrink-0` so the `flex-1 min-w-0 truncate` header title cannot squeeze them at 390px. Rationale: one reusable component, no duplicated markup, no shared state machine.
- **Tailwind mode:** `darkMode: 'class'` in `tailwind.config.js`. Alternative (`media`) rejected because it cannot be user-toggled.
- **Token mapping:** dark companions appended to each light token. Page surfaces and dialogs `bg-white dark:bg-slate-900`; subtle fills `bg-slate-50/100 dark:bg-slate-800`; primary `ink` `text-slate-800 dark:text-slate-100`, `text-slate-700 dark:text-slate-200`, `text-slate-600 dark:text-slate-300` (the last is critical: slate-600 on slate-900 is ≈2.1:1); muted `text-slate-500 dark:text-slate-400`; `text-slate-400/300` unchanged. Every pastel badge becomes `dark:bg-*-500/15 dark:text-*-300 dark:border-white/10`. Focus ring offset `ring-offset-white dark:ring-offset-slate-900`; selection, scroll-slim thumb, and the hardcoded select-chevron SVG stroke get dark rules in `index.css`. `color-scheme` on `<html>` keeps native `<dialog>` and scrollbars dark.
- **Script-derived tones:** `Audit.vue` `actionTone()` returns class strings; each returned string gets the same dark companions so audit action badges are not missed by a template-only pass.
- **Unchanged:** indigo primary buttons/FAB, the login indigo gradient panel, the dark sidebar, `accent-indigo-600` checkboxes, every `min-h-*`, `truncate`, `md:hidden`/`hidden md:block` card/table split, `aria-*`, and all handlers.

## Risks / Trade-offs

- [Risk] FOUC from deferred module execution → Mitigation: synchronous inline head script before the stylesheet link; Playwright assertions seed `localStorage.theme='dark'` and `localStorage.theme='system'` with OS dark, navigate, and check `.dark` + `colorScheme` + computed dark body background, plus a static assertion that the script precedes the stylesheet link in `dist/index.html`.
- [Risk] Pastel badges unreadable → Mitigation: paired `dark:bg-*/15` + `dark:text-*-300` for every badge, including script-derived audit tones.
- [Risk] `text-slate-600` too dark on slate-900 → Mitigation: `dark:text-slate-300` everywhere it appears (Login labels, A2UI renderer, list empty states).
- [Risk] Mobile header crowding → Mitigation: `shrink-0` on the toggle; hamburger is `md:hidden`, collapse is `hidden md:grid`, and the title is `flex-1 min-w-0 truncate`.
- [Trade-off] A cycling icon button is less discoverable than a labelled select — mitigated by `aria-label`/`title` naming current and next mode and a monitor icon for system; chosen because no settings view exists and a select would add markup and state.

## Migration Plan

1. Add the inline theme script, `darkMode: 'class'`, `ThemeToggle.vue`, and `index.css` dark rules.
2. Apply the token map across `App.vue`, components, and views; grep gate confirms no light token lacks a `dark:` companion.
3. `npm run build`, `docker compose up -d --build ui`, pytest, and Playwright checks at 390×844 and 1200×900.
4. Rollback: revert the theme script/toggle/config and strip `dark:` variants — no data or API migration involved.
