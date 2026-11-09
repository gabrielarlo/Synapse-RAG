## ADDED Requirements

### Requirement: Document replacement with version increment

The system SHALL allow an authorized user to replace a document's content in place, incrementing its `version`, deleting its previous vectors and outstanding ingestion jobs, and queueing re-ingestion; a replacement that fails before the database transaction commits SHALL leave the previous file, vectors, version and status unchanged.

#### Scenario: Authorized replace bumps the version

- **WHEN** an authorized user replaces a document's file
- **THEN** the document's version increases by one, its previous vectors are removed, a new ingestion job is queued with the document's scope, and the response reports the new version

#### Scenario: Replace failure preserves the document

- **WHEN** a replacement exceeds the upload limit or the database write fails
- **THEN** the previous file bytes, vectors, version and status remain in place and the request reports the failure

#### Scenario: Superseded worker writes nothing

- **WHEN** a document is replaced while a worker is still ingesting its previous job
- **THEN** that worker's chunk write and job completion are rejected and no ingest event is logged for it

### Requirement: Document deletion

The system SHALL allow an authorized user to delete a document together with its vectors, ingestion jobs and stored file.

#### Scenario: Delete removes every trace

- **WHEN** an authorized user deletes a document
- **THEN** the document, its vectors, its jobs and its stored file are gone and it no longer appears in listings

#### Scenario: Unauthorized or unknown delete rejected

- **WHEN** a user without access deletes a document, or the id is unknown or malformed
- **THEN** the system responds 403 or 404 respectively and deletes nothing

### Requirement: Document management authorization

Admins SHALL manage every document; account documents SHALL require membership of that account; internal documents SHALL be changeable only by their uploader or an admin. Every replacement and deletion SHALL be recorded in the audit trail.

#### Scenario: Staff manages own internal document

- **WHEN** a staff user replaces or deletes an internal document they uploaded
- **THEN** the operation succeeds and an audit event records it

#### Scenario: Staff blocked from another internal document

- **WHEN** a staff user attempts to change an internal document uploaded by someone else
- **THEN** the system responds 403

### Requirement: Decision-model category tagging

The system SHALL tag each ingested document with a category from the fixed taxonomy `policy`, `contract`, `technical`, `billing`, `hr`, `other`, produced by the configured decision model; a tagging failure SHALL leave the category empty without failing ingestion.

#### Scenario: Ingested document carries a category

- **WHEN** ingestion completes for a document
- **THEN** the document status reads `ready` and its category is one of the taxonomy values

#### Scenario: Tagging failure does not fail ingestion

- **WHEN** the decision model is unavailable while tagging
- **THEN** the document still reads `ready` with an empty category and its vectors remain searchable

### Requirement: Image text extraction

The system SHALL extract text from uploaded images through a vision-capable model before chunking; a document whose image yields no text, exceeds the extraction size limit, or cannot be processed SHALL fail with an operator-visible error rather than storing binary content as text.

#### Scenario: Image is transcribed

- **WHEN** an image document is ingested
- **THEN** its chunks contain the transcribed text and its status reads `ready`

#### Scenario: Unextractable image fails cleanly

- **WHEN** OCR returns no text, the image is too large, or no vision model is configured
- **THEN** the document status reads `failed` with a reason and no binary content is stored as text

### Requirement: Read-only document view

The system SHALL expose a read-only document detail returning its metadata plus a bounded, ordinally ordered excerpt of its extracted chunk text, authorized the same way as listing: admins for any document, account membership for account documents, and any authenticated user for internal documents.

#### Scenario: Authorized view returns metadata and text

- **WHEN** an authorized user opens a document's detail
- **THEN** the response carries the document's metadata, its chunk text in order, the full chunk count, and whether the excerpt was truncated

#### Scenario: Excerpt is bounded

- **WHEN** a document has more chunks than the excerpt limit
- **THEN** only the first chunks are returned and the response reports the full count with the truncated flag

#### Scenario: Unauthorized view rejected

- **WHEN** a user without access to the document's account requests it, or the request is unauthenticated
- **THEN** the system responds 403 or 401 respectively and returns no document content
