# Proposal — strict scope authorization

## Why

Chat retrieval and document lists currently merge internal documents into
every account scope, so asking under account "Hugo" answers from shared
internal content even though the user asked for one scope. And internal
documents can be replaced/deleted by their uploader, not only admins.

## What Changes

- **BREAKING**: chat retrieval scope is exactly one — the selected account's
  documents, or internal documents when `internal` is chosen (account scope
  no longer includes internal; internal scope already was internal-only).
- **BREAKING**: document lists follow the same single-scope rule.
- Internal documents may be **viewed, replaced or deleted by admins only**;
  staff may still upload (create) internal documents they cannot later
  open or change.
- Admin bypass is unchanged: admins see and manage everything.

## Capabilities

- **Modified Capabilities**
  - `document-ingestion` — single-scope listing; admin-only management of
    internal documents (supersedes "Account-or-internal document scoping" and
    the management half of "Document management authorization").
  - `rag-answering` — single-scope retrieval (supersedes "RLS-gated
    retrieval scoped to one resolved account plus internal").

## Impact

- API: `api/app/store.py`, `api/app/db.py` (`list_documents`, `search`,
  single-scope `WHERE` + nil-UUID `current_account` sentinel for internal
  scope; RLS policies unchanged), `api/app/routers/documents.py`
  (`_authorize`, view), chat retrieval already scoped by `Scope`.
- UI: Documents/Chat views already send exactly one scope; no new params.
- External FAQ unchanged (own account only, never internal).
