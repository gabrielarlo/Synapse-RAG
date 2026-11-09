# Document Ingestion Specification

## Purpose

Lets staff upload documents that become searchable vectors so RAG answers are grounded in tenant-scoped knowledge rather than model memory alone.

## Requirements

### Requirement: Authenticated document upload

The system SHALL accept document uploads only from authenticated users with access to the target scope, recording uploader, timestamp, and scope.

#### Scenario: Authorized upload succeeds

- **WHEN** a staff user uploads a document to an assigned account
- **THEN** the system stores the file metadata and queues it for ingestion

#### Scenario: Unauthorized upload rejected

- **WHEN** a staff user uploads to an account not assigned to them
- **THEN** the system responds 403 and stores nothing

### Requirement: Ingestion into PGVector via Ollama embeddings

The system SHALL chunk uploaded documents, embed chunks with the configured Ollama embedding model, and store vectors in PGSQL with `pgvector`, marking ingestion status per document.

#### Scenario: Successful ingestion searchable

- **WHEN** ingestion completes for a document
- **THEN** its chunks are retrievable by vector similarity and status reads `ready`

#### Scenario: Failed ingestion surfaces error

- **WHEN** embedding or storage fails
- **THEN** the document status reads `failed` with an operator-visible error and no partial silent success

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

### Requirement: PG-backed ingestion job queue

Ingestion SHALL run asynchronously via a PGSQL-backed job table polled by the worker service (no external broker); upload SHALL create a `pending` job and return immediately, and the worker SHALL claim jobs and mark them `ready` or `failed`.

#### Scenario: Upload returns before ingestion finishes

- **WHEN** a user uploads a document
- **THEN** the API responds with a queued status and a job id without waiting for embedding to complete

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
