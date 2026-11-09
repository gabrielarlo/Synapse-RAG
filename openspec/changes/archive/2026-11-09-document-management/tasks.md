# Tasks — document management

## 1. Schema

- [x] 1.1 Add `documents.version` (default 1) and `documents.category` in `infra/migrations/004_document_versions.sql`, applied to the running database

## 2. Store layer

- [x] 2.1 InMemoryStore and PostgresStore: `get_document`, `replace_document` (version bump, chunk/job purge, scope-carrying job), `delete_document`
- [x] 2.2 Job-gated `add_chunks(..., job_id)` and `finish_job(..., category, document_id)`; every ingest-path transaction locks the document row first
- [x] 2.3 `search` returns each chunk's document category; list/create responses include `version` and `category`

## 3. API

- [x] 3.1 `PUT /api/documents/{id}`: temp file under cap, hard-link backup, `os.replace`, version-bumping transaction, restore on failure
- [x] 3.2 `DELETE /api/documents/{id}`: single cascading delete plus file cleanup
- [x] 3.3 Authorization (admin / account member / internal uploader), UUID validation, audit events for replace and delete

## 4. Worker

- [x] 4.1 Pass `job_id` to `add_chunks`; pass `document_id` and category to `finish_job`; skip the ingest audit event for superseded jobs
- [x] 4.2 `Ollama.tag_document` over `/v1/systemone` with taxonomy validation; tagging failures leave the category empty

## 5. Chat

- [x] 5.1 Report the retrieved documents' category when unanimous, otherwise the triage category

## 6. UI

- [x] 6.1 Version and Category columns plus Replace/Delete row actions; `replaceDocument`/`deleteDocument` in `api.js`
- [x] 6.2 View action opening a modal with metadata and a bounded chunk excerpt; focus trap, Esc/backdrop close, focus restore

## 7. Verification

- [x] 7.1 Hermetic tests: version bump, scope-carrying job, stale-worker rejection on replace and delete, oversize preservation, file restore on database failure, concurrent replace serialization, authorization matrix, tagging failure, chat category rule, list fields
- [x] 7.2 Read-view tests: metadata + ordered text, 401/403/404 matrix, chunk cap and truncation; live-PG ordering/count assertion in the opt-in suite
- [x] 7.3 Full pytest suite green; `docker compose config`; api/worker/ui rebuilt and Up
- [x] 7.4 Live smoke: staff-uploaded internal document replaced (RLS path) reaching `ready` with a category, then deleted
- [x] 7.5 Playwright: View modal renders metadata and text, closes on Esc, focus returns to the page

## 8. Duplicate-name upload + updated_at

- [x] 8.1 `infra/migrations/005_document_updated_at.sql`: `documents.updated_at`, set on replace; stores return it on create/get/list/replace, PUT response includes it
- [x] 8.2 UI upload checks the scoped list for the same filename and confirms (`"…" already exists (vN). Upload as a newer version?`); confirmed uploads call Replace (new version, re-ingest); view modal shows Updated
- [x] 8.3 Hermetic test: replace bumps `updated_at`; full suite green; migration applied to live DB; api/ui rebuilt and Up
- [x] 8.4 Regression fix: duplicated `fetchone()` guard made PG `replace_document` return None (phantom 404 after commit); verified against live PG, api rebuilt
- [x] 8.5 Relative timestamps (`moments ago`, `5 minutes ago`, …) in the view modal; `uploaded_by` resolved to username in `GET /api/documents/{id}`; api/ui rebuilt and Up
- [x] 8.6 Upload 413 fix: `client_max_body_size 50m` in `ui/nginx.conf` (matched `MAX_UPLOAD_MB`; nginx default 1m rejected uploads with HTML before API); `errorDetail()` in `api.js` surfaces real errors (status/network) in Documents view; ui rebuilt and Up
