# Document management: replace, delete, and decision-model categories

## Why

Documents were upload-only: a wrong or outdated file could not be corrected or
removed, so stale vectors kept answering questions, and the only way to fix a
document was SQL against the database. Category labels on chat answers came
purely from the triage model, with no knowledge of what the retrieved
documents actually are.

## What changes

- `PUT /api/documents/{id}` replaces a document's content: version + 1, old
  vectors dropped, re-ingestion queued. The previous file survives any failure
  (upload cap, database error).
- `DELETE /api/documents/{id}` removes the document with its vectors, jobs and
  stored file.
- The ingestion worker tags each document with a decision-model category
  (`policy`, `contract`, `technical`, `billing`, `hr`, `other`), stored on
  `documents.category`.
- Chat reports the retrieved documents' category when every retrieved chunk is
  tagged and they agree; otherwise it keeps the triage category.

## Impact

- Migration `004_document_versions.sql`: `documents.version`, `documents.category`.
- API: new `PUT`/`DELETE` on `/api/documents/{id}`; list responses gain
  `version` and `category`.
- Worker: job-gated chunk writes and finishes, plus tagging.
- UI: Version/Category columns and Replace/Delete actions.
