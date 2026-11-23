# chat-session-metadata Specification

## Purpose
Makes chat history row metadata accurate: the displayed message count and preview match the turns in the thread that opens when the row is selected, including audit exchanges.

## Requirements

### Requirement: Accurate session metadata

The system SHALL report, for each listed chat session, a message count equal to the number of persisted turns in that session and a preview taken from its first user turn. Audit exchanges SHALL be included in both.

#### Scenario: Audit-only session reports its real count

- **WHEN** a session contains one `audit: ` user question and its `audit`-categorized assistant answer
- **THEN** the history row reports `count = 2` and a preview of that user question, and opening the row shows those same two turns

#### Scenario: Normal session unchanged

- **WHEN** a session contains one ordinary question and answer
- **THEN** the row reports `count = 2` and a preview of the first user message

#### Scenario: Expired sessions still listed

- **WHEN** a session's last activity is older than the context TTL
- **THEN** it is still listed with metadata matching its persisted turns

### Requirement: Listing behavior unchanged

The system SHALL keep the existing owner-only listing, ordering, limit, and read-only behaviour; correcting metadata SHALL NOT change which sessions appear or touch `last_active`.

#### Scenario: No side effects from metadata

- **WHEN** sessions are listed
- **THEN** no `last_active` value changes and no session is added, removed, or reordered by the metadata calculation
