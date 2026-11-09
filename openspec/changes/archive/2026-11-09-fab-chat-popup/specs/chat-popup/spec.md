# Spec Delta

## Purpose

Lets users chat in place from any page via a popup without losing current page context.

## ADDED Requirements

### Requirement: Chat popup open/close

The system SHALL open a chat popup when the global FAB is activated and SHALL close it without navigating away. The popup SHALL be hidden on `/chat` and `/login`.

#### Scenario: Open from another page

- **WHEN** user activates FAB on Documents/Accounts/Staff/Audit
- **THEN** chat popup opens and URL stays unchanged

#### Scenario: Close via toggle or dismiss

- **WHEN** user clicks FAB again, close button, or presses Escape
- **THEN** popup closes and underlying page is unchanged

#### Scenario: Send message in popup

- **WHEN** user sends a message in the popup
- **THEN** answer appears in the popup and the same session is shared with `/chat` page

### Requirement: Chat popup accessibility and persistence

The system SHALL keep the popup's live session in the same `chat_session` storage as `/chat`. The popup SHALL be focus-managed (focus moves in on open, returns to FAB on close) and SHALL respect read-only/history state identically to the page.

#### Scenario: Session continuity

- **WHEN** user chats in popup then navigates to `/chat`
- **THEN** the same session thread is restored
