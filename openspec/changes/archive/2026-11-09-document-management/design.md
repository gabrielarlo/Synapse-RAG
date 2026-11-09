# Design — document management

## Replace semantics

A replace keeps the document identity (so audit references stay valid) and
increments `version`. The whole mutate sequence — file swap plus database
transaction — runs under a per-document in-process lock, because the file bytes
and the row must belong to the same request.

Order inside the transaction is fixed: the `documents` row is updated (taking
its row lock) first, then chunks and jobs are deleted, then a new job is
inserted carrying the document's scope. Every ingest-path transaction follows
the same order, so no pair of them can deadlock.

## File safety

The new bytes land in a temp file under the upload cap; the previous file is
hard-linked to a unique backup so it is never absent (a worker read cannot see a
missing file), and the backup is restored if the transaction fails. A document
that vanished mid-replace leaves no orphan file.

## Stale worker writes

A worker can be mid-ingest when a document is replaced or deleted. Chunk writes
and job completion are gated on the job still existing for that document, so a
superseded worker writes nothing, finishes nothing and logs no ingest event.
This also removes the previous behaviour where a deleted job made the worker
raise out of its error handler.

## Categories

The worker asks the decision model for one of six categories after a successful
chunk write and passes it to the job-gated finish; a tagging failure leaves the
category NULL and the document `ready` — ingestion never fails over a tag.
Chat prefers the retrieved documents' category only when every retrieved chunk
is tagged and they agree, so one tagged document cannot relabel an answer built
from untagged or mixed sources.

## Authorization

Admins manage everything. Account documents require membership of that account.
Internal documents are shared across tenants, so only their uploader or an
admin may change them.
