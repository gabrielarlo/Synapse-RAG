# Proposal

## Why

Chat history rows can say "0 messages" while the opened thread visibly contains an `audit: …` question and its answer. `SessionStore.list_sessions()` deliberately excluded audit turns from the row's `count` and `preview`, so audit-only sessions looked empty. The user reported this as inaccurate and asked for the displayed metadata to match the thread.

## What Changes

- Count every persisted turn in `list_sessions()` (`count = len(turns)`) and take the preview from the first user turn, including `audit: ` questions and assistant turns categorized `audit`.
- Update the one test that asserted the old exclusion and the stale comment in `chat.py` that described it.
- No UI change: `ChatPanel.vue` already renders `count` and `preview` from the API payload. No change to which sessions are listed, ordering, limits, TTL behaviour, audit logging, or the delete flow. No **BREAKING** changes.

## Capabilities

### New Capabilities

- `chat-session-metadata`: history rows report a message count and preview that match the persisted thread, including audit exchanges.

### Modified Capabilities

- None

## Impact

- Affected code: `api/app/sessions.py`, `api/app/routers/chat.py` (comment only), `tests/test_sessions.py`, new OpenSpec change.
- API response shape is unchanged; only the `count` and `preview` values for audit-containing sessions change. Clients that render them (ChatPanel history rail) become accurate without edits.
- Risk: none to authorization or data; the previous exclusion existed only in a test comment and a docstring, not in a published main spec.
