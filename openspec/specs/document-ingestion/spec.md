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

Each document SHALL be attached to exactly one account or marked `internal`, and retrieval SHALL never leak a document outside its scope.

#### Scenario: Account document isolated

- **WHEN** a query runs under account A
- **THEN** results exclude documents of account B and include account A plus `internal` documents only as the requester's role permits

#### Scenario: Scope missing rejected

- **WHEN** an upload specifies neither an account nor `internal`
- **THEN** the system rejects it with 422

### Requirement: PG-backed ingestion job queue

Ingestion SHALL run asynchronously via a PGSQL-backed job table polled by the worker service (no external broker); upload SHALL create a `pending` job and return immediately, and the worker SHALL claim jobs and mark them `ready` or `failed`.

#### Scenario: Upload returns before ingestion finishes

- **WHEN** a user uploads a document
- **THEN** the API responds with a queued status and a job id without waiting for embedding to complete
