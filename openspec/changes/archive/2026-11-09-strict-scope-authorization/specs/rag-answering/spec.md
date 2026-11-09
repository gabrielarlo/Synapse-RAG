## MODIFIED Requirements

### Requirement: RLS-gated retrieval scoped to one resolved account plus internal

The system SHALL enforce PGSQL row-level security on every retrieval path using the single resolved `account_id`: for an account scope, results SHALL include only that account's documents; for the internal scope, results SHALL include only internal documents; all other content SHALL be excluded. External FAQ callers are scoped to their own credential-bound account and SHALL NOT receive `internal` documents.

#### Scenario: Cross-account leak blocked

- **WHEN** a user scoped to account A queries a topic documented only under account B
- **THEN** the system answers without account B content (abstains or uses only allowed scope) and never exposes B's chunks

#### Scenario: Internal docs excluded from account scope

- **WHEN** a user scoped to account A queries a topic documented only in `internal` documents
- **THEN** the system answers without internal content (abstains or uses only account A documents)

#### Scenario: Internal documents visible internally only

- **WHEN** an external FAQ caller queries a topic documented only in `internal` documents
- **THEN** the system withholds the `internal` content
