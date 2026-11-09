# Design

## Context

`App.vue` renders a `RouterLink to="/chat"` FAB (hidden on `/chat`). `Chat.vue` holds the full inbox+thread/composer with `localStorage chat_session` persistence. See `proposal.md` for why.

## Goals / Non-Goals

**Goals:** In-place popup reusing one chat implementation; no navigation; shared session.

**Non-Goals:** No backend change; no new chat engine; no FAB redesign.

## Decisions

- Extract `Chat.vue` body into `ChatPanel.vue` (props: `compact`) reused by both `/chat` view and popup; single source of truth.
- `App.vue` holds `popupOpen` state; FAB becomes `<button @click="popupOpen = !popupOpen">`; popup is fixed bottom-right card (max-h, overflow), `role="dialog" aria-modal="false"`, Escape/backdrop/FAB-toggle close, focus trap light (focus in/out).
- Prevent duplicate mount: `v-if="popupOpen && route.path !== '/chat'"` on the dialog mount + `watch(route.path, () => popupOpen = false)` + close on logout; only one `ChatPanel` ever mounted.
- Popup mounts `ChatPanel` only when open (no polling when closed). In compact: rail/search hidden; `+ New chat` moves into the compact header row (visible in popup) so popup can start a new session; thread+composer otherwise identical.
- Alternatives: iframe (rejected: double auth/session complexity), duplicate mini-chat (rejected: divergent behavior).

## Risks / Trade-offs

- Popup height on small screens → constrain `max-h-[80vh]`, thread scrolls internally.
- Focus loss on close → return focus to FAB explicitly.
- Duplicate rendering on `/chat` + popup → only one mounted at a time (FAB hidden on `/chat`).
