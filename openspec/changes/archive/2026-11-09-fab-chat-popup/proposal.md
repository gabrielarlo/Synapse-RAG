# Proposal

## Why

The global FAB button (blue circle in screenshot) currently redirects to `/chat`, losing the user's current page context. Users want in-place chat without navigation.

## What Changes

- Replace `RouterLink to="/chat"` FAB with a toggle button that opens a chat popup overlay.
- Popup reuses existing chat logic (send, scope, session) without route change; closing returns to the underlying page.
- FAB hidden on `/chat` and `/login` remains; behavior on other pages changes from navigate to open popup.

## Capabilities

### New Capabilities
- `chat-popup`: In-place chat popup opened from global FAB.

### Modified Capabilities
- `platform-foundation`: FAB navigation behavior changes (navigate → popup). UI shell only; no API/spec change to chat backend.

## Impact

- `ui/src/App.vue` (FAB → button + popup container).
- `ui/src/views/Chat.vue` or extracted `ChatPanel` reused in popup (shared state, no duplicate API calls).
- No backend/API change. Tests: FAB visibility + popup open/close + keyboard/aria.
