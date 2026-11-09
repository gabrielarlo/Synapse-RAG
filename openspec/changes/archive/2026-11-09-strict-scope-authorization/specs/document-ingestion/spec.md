## MODIFIED Requirements

### Requirement: Account-or-internal document scoping

Each document SHALL be attached to exactly one account or marked `internal`, and retrieval and listing SHALL never leak a document outside the single requested scope: an account scope exposes only that account's documents, an internal scope exposes only internal documents, and admins retain access to everything.

#### Scenario: Account document isolated

- **WHEN** a query runs under account A
- **THEN** results include only account A's documents and exclude account B's and all internal documents

#### Scenario: Internal scope isolated

- **WHEN** a query runs under the internal scope
- **THEN** results include only internal documents and exclude every account's documents

#### Scenario: Scope missing rejected

- **WHEN** an upload specifies neither an account nor `internal`
- **THEN** the system rejects it with 422

### Requirement: Document management authorization

Admins SHALL manage every document; account documents SHALL require membership of that account; **internal documents SHALL be replaceable or deletable by admins only**, with staff limited to creating (uploading) them. Every replacement and deletion SHALL be recorded in the audit trail.

#### Scenario: Staff manages own internal document

- **WHEN** a staff user replaces or deletes an internal document they uploaded
- **THEN** the system responds 403 — only admins manage internal documents

#### Scenario: Staff blocked from another internal document

- **WHEN** a staff user attempts to change an internal document uploaded by someone else
- **THEN** the system responds 403

#### Scenario: Admin manages an internal document

- **WHEN** an admin replaces or deletes an internal document uploaded by anyone
- **THEN** the operation succeeds and an audit event records it

#### Scenario: Staff may still upload internal documents

- **WHEN** a staff user uploads a new internal document
- **THEN** the upload succeeds and the document is queued for ingestion

### Requirement: Read-only document view

The system SHALL expose a read-only document detail returning its metadata plus a bounded, ordinally ordered excerpt of its extracted chunk text, authorized by scope: admins for any document, account membership for account documents, and **admins only for internal documents**.

#### Scenario: Authorized view returns metadata and text

- **WHEN** an authorized user opens a document's detail
- **THEN** the response carries the document's metadata, its chunk text in order, the full chunk count, and whether the excerpt was truncated

#### Scenario: Excerpt is bounded

- **WHEN** a document has more chunks than the excerpt limit
- **THEN** only the first chunks are returned and the response reports the full count with the truncated flag

#### Scenario: Staff view of internal document rejected

- **WHEN** a non-admin user requests an internal document's detail
- **THEN** the system responds 403 and returns no document content

#### Scenario: Unauthorized view rejected

- **WHEN** a user without access to the document's account requests it, or the request is unauthenticated
- **THEN** the system responds 403 or 401 respectively and returns no document content
