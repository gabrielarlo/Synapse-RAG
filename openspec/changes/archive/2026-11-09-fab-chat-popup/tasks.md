# Tasks

## 1. Extract chat panel

- [x] 1.1 Extract `Chat.vue` to `ChatPanel.vue` with `compact` prop; verify `/chat` renders identically (Playwright screenshot + manual).
- [x] 1.2 Hide inbox rail/search in `compact` mode, move `+ New chat` into the compact header row; verify popup has New chat + thread+composer only (manual).

## 2. Popup shell

- [x] 2.1 Change FAB `RouterLink` to button toggling `popupOpen` in `App.vue`; verify URL unchanged on toggle (Playwright).
- [x] 2.2 Add popup dialog (role/dialog, Escape/close, focus return to FAB); verify keyboard flow (Playwright).

## 3. Verification

- [x] 3.1 Run `pytest tests/ -q` and `docker compose up -d --build ui api`; verify FAB hidden on `/chat`+`/login`, popup send shares session with `/chat`, and open-popup → sidebar Chat yields exactly one panel at `/chat` (Playwright).
