# chat-session-deletion Specification

## Purpose
Provides an owner-scoped, audited way to permanently delete a persisted chat session from the history rail.

## Requirements

### Requirement: Owner-scoped session deletion endpoint

The system SHALL expose `DELETE /api/chat/sessions/{session_id}` that deletes a session only for its owning user, requiring account membership for account-scoped sessions, and SHALL return 404 for unknown ids, 403 for other users, and 401 for unauthenticated callers.

#### Scenario: Owner deletes a session

- **WHEN** the owning user deletes one of their sessions
- **THEN** the response is 200, the session is gone from the history list, and its history endpoint returns 404

#### Scenario: Foreign or unknown session is rejected

- **WHEN** another user attempts to delete the session, or the id does not exist, or the caller is unauthenticated
- **THEN** the response is 403, 404 or 401 respectively and the session remains

#### Scenario: Revoked account membership is enforced

- **WHEN** the owning user no longer belongs to the account the session is bound to
- **THEN** the deletion is rejected with 403, mirroring the history endpoint

### Requirement: Complete session cleanup

The system SHALL remove the session row, all of its `session_turns` rows and all corresponding `session_meta` rows. No child rows SHALL remain after deletion.

#### Scenario: No orphaned rows remain

- **WHEN** a session with multiple turns is deleted
- **THEN** `sessions`, `session_turns` and `session_meta` contain no rows for that session or its turn ids

### Requirement: Deletion is audited

The system SHALL record a `delete` audit event with the acting username, the bound account (or none for internal sessions) and the deleted session id.

#### Scenario: Audit event recorded

- **WHEN** a session is deleted successfully
- **THEN** an audit event with action `delete` and detail naming the session id is recorded

### Requirement: Confirming UI action

The system SHALL provide a trash button on each chat history row except Live chat, and SHALL require a confirmation dialog naming the exact conversation and its permanent consequence before deleting.

#### Scenario: Confirmation is required and specific

- **WHEN** a user activates a row's trash button
- **THEN** a dialog opens naming that conversation (resolved to a human-readable account name or "Internal", never a UUID), stating that the conversation and its messages are permanently deleted, with a neutral Cancel and a visually distinct danger Delete action

#### Scenario: Cancel and success

- **WHEN** the user cancels, or confirms successfully
- **THEN** the row is unchanged on cancel, and on success only that row is removed from the history list

#### Scenario: Failure is non-destructive

- **WHEN** the delete request fails
- **THEN** the row remains and an error is shown

#### Scenario: Active session cleanup

- **WHEN** the deleted session is the live session or the one being viewed
- **THEN** the UI clears that session and returns to a fresh Live chat state

### Requirement: Accessibility and mobile layout preserved

The system SHALL keep the history rail keyboard-navigable and free of horizontal scrolling on phones after adding the delete button.

#### Scenario: Arrow keys skip the delete button

- **WHEN** a user presses ArrowDown/ArrowUp inside the history list
- **THEN** focus moves through Live chat and session rows only, never onto a trash button

#### Scenario: Mobile touch targets

- **WHEN** the viewport is 390×844
- **THEN** each trash button is at least 44×44 CSS pixels and `scrollWidth === clientWidth`
