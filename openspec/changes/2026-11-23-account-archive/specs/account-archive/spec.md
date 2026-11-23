# Spec Delta

## Purpose

Adds a reversible admin-only account archive state that takes a tenant's knowledge out of retrieval without deleting any of its data.

## ADDED Requirements

### Requirement: Account archive state

The system SHALL let an admin archive and unarchive an account by id. The state SHALL be persisted on the account, SHALL be idempotent, SHALL be recorded in the audit trail, and SHALL NOT delete the account, its documents, assignments, credentials or audit history. An unknown id SHALL return 404 and a non-admin SHALL receive 403 with no state change.

#### Scenario: Admin archives an account

- **WHEN** an admin posts to the archive endpoint with an existing account id
- **THEN** the account is marked archived, the response succeeds, and an `account_archive` audit event is appended

#### Scenario: Admin unarchives an account

- **WHEN** an admin posts to the unarchive endpoint for an archived account
- **THEN** the account is marked active again, its documents become retrievable, and an `account_unarchive` audit event is appended

#### Scenario: Unknown target and non-admin rejected

- **WHEN** an unknown id is posted or a staff user calls either endpoint
- **THEN** the system responds 404 for the unknown id and 403 for the staff user, changing no account

### Requirement: Archived accounts are out of scope

The system SHALL exclude an archived account's documents, chunks and ingestion jobs from chunk search, document listings, document reads and worker job claiming, for every caller including admins. Scope resolution for an archived account SHALL be refused with 403 `account archived` so no new chat or external FAQ scope can be opened on it. Unarchive SHALL restore access without data migration. Archived accounts SHALL remain visible to admins with a badge and SHALL be hidden from staff account lists.

#### Scenario: Retrieval cascade

- **WHEN** an account is archived while it has ready documents and chunks
- **THEN** those documents are absent from document listings, chunk search returns nothing for that scope, and the worker does not claim its pending jobs; documents of other accounts are unaffected

#### Scenario: Archived scope refused

- **WHEN** a user asks to chat with an archived account, or an external FAQ request uses a credential for an archived account
- **THEN** the system responds 403 `account archived` and performs no retrieval; the external path is guarded directly because it does not use `resolve_scope`

#### Scenario: Active accounts unaffected

- **WHEN** an active account is used for chat, document management or external FAQ
- **THEN** behavior is unchanged from before this capability existed

### Requirement: Account archive UI

The Accounts page SHALL show an archive icon action on active account rows and an `Archived` badge plus an unarchive action on archived rows. Archive SHALL require a confirmation dialog naming the exact account and stating that its documents become unavailable until unarchived, with a danger-styled confirm control and an autofocused Cancel that makes no request. Unarchive SHALL be immediate. Both actions SHALL refresh the list, show a status message, display no raw UUIDs, and remain usable at 390px with no horizontal scrolling.

#### Scenario: Confirm and cancel

- **WHEN** an admin opens the archive confirmation for a named account
- **THEN** the dialog names that account and the consequence; Cancel closes it without a request, while confirm archives the account, shows the badge and removes the archive action

#### Scenario: Staff view

- **WHEN** a staff user views the Accounts page
- **THEN** no archive or unarchive control is offered
