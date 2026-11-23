# Tasks

## 1. Theme bootstrap and toggle

- [x] 1.1 Add a synchronous inline head script to `ui/index.html` reading the stored preference (`localStorage['theme']`, default `system`, valid values `light`/`dark`/`system`), computing effective dark, and setting `.dark`, `colorScheme` and `data-theme` on `<html>` — verify in built `dist/index.html` that the script precedes the stylesheet link and that seeded dark and seeded system-with-OS-dark paint dark with no flash.
- [x] 1.2 Set `darkMode: 'class'` in `ui/tailwind.config.js` — verify `npm run build` emits `dark:` utilities.
- [x] 1.3 Create `ThemeToggle.vue` with mode read from the stored preference (never the `.dark` class), a light → dark → system cycle, sun/moon/monitor icons, `aria-label`/`title` naming current and next mode, `data-theme`, and a `matchMedia` change listener that follows OS changes only in system mode — verify Playwright cycles all three modes, restores the exact mode on reload (monitor icon for system), and follows a live OS change without reload while ignoring it in explicit modes.
- [x] 1.4 Mount the toggle in `App.vue` header and `Login.vue` form column — verify both are ≥44px at 390px and `scrollWidth === clientWidth`.

## 2. Dark token coverage

- [x] 2.1 Add dark rules to `ui/src/index.css` for body/background gradient, `::selection`, focus ring offset, scroll-slim thumb, and the select chevron SVG — verify computed styles in both themes.
- [x] 2.2 Apply the token map to `App.vue` and components (`BaseInput`, `ChatPanel`, `ChatBox`, `A2UIRenderer`) — verify chat bubbles, composer, history rail, popup and A2UI cards are readable in dark mode.
- [x] 2.3 Apply the token map to all views (`Login`, `Chat`, `Documents`, `Accounts`, `Staff`, `Audit`), including `Audit.vue` script-derived action tones and `<form method="dialog">` dialogs — verify every page's cards, tables, badges, errors and dialogs in dark mode.
- [x] 2.4 Broadened grep gate finds zero light tokens without a `dark:` companion (documented exemptions: dark sidebar and indigo gradient panel).

## 3. Gates

- [x] 3.1 Run `npm run build` and `docker compose config`, then `docker compose up -d --build ui` and assert the `ui` container is Up.
- [x] 3.2 Run `.venv/bin/python -m pytest tests/ -q` green.
- [x] 3.3 Playwright at 390×844 and 1200×900: `scrollWidth === clientWidth`, cards on mobile / table only on desktop, toggle contrast, persistence of all three modes, live system following, and seeded-theme no-FOUC assertions.
