import glob
import os
import shutil
import threading
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ..deps import authed, resolve_scope
from ..store import User

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Serializes the whole mutate sequence (file swap + DB tx) per document so the
# file bytes and the DB row always belong to the same request. Unbounded on
# purpose: one tiny lock per document, and evicting entries can hand two
# threads different locks for the same document.
# shortcut: in-process only — correct for the single-replica api service;
# upgrade to pg_advisory_xact_lock if the API is ever scaled out.
_doc_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(document_id: str) -> threading.Lock:
    with _locks_guard:
        return _doc_locks.setdefault(document_id, threading.Lock())


def _norm_id(raw: str) -> str:
    try:
        return str(uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(404, "unknown document")


def _authorize(store, user: User, doc: dict) -> None:
    """Admins manage everything; account docs need membership; internal docs
    belong to their uploader."""
    if user.role == "admin":
        return
    if doc["account_id"]:
        if not store.is_member(user.id, doc["account_id"]):
            raise HTTPException(403, "not assigned to this account")
    elif doc["uploaded_by"] != user.id:
        raise HTTPException(403, "only the uploader or an admin can change"
                                 " an internal document")


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


@router.post("", response_model=dict)
async def upload(request: Request, account_id: str | None = None,
                 internal: bool = False, file: UploadFile = File(...),
                 user: User = Depends(authed)):
    c = request.app.state.ctx
    if account_id is None and not internal:
        raise HTTPException(422, "account_id or internal=true is required")
    if account_id is not None:
        resolve_scope(request, account_id, user)  # 403 if unassigned
    try:
        res = c["store"].create_document(file.filename or "upload",
                                         account_id, internal, user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    c["store"].log(actor=user.username, action="upload",
                   account_id=account_id, detail=file.filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, res["document"]["id"])
    cap = c["settings"].MAX_UPLOAD_MB * 1024 * 1024
    size, too_big = 0, False
    with open(dest, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > cap:
                too_big = True
                break
            f.write(chunk)
    if too_big:
        os.unlink(dest)
        raise HTTPException(413, f"file exceeds {c['settings'].MAX_UPLOAD_MB} MB")
    return {"job_id": res["job_id"], "status": "queued",
            "document_id": res["document"]["id"]}


@router.put("/{document_id}", response_model=dict)
def replace(document_id: str, request: Request, filename: str | None = None,
            file: UploadFile = File(...), user: User = Depends(authed)):
    """Replace a document's content: version + 1, old vectors dropped, re-queued."""
    c = request.app.state.ctx
    store = c["store"]
    did = _norm_id(document_id)
    doc = store.get_document(did)
    if doc is None:
        raise HTTPException(404, "unknown document")
    _authorize(store, user, doc)

    with _lock_for(did):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        dest = os.path.join(UPLOAD_DIR, did)
        tmp = f"{dest}.tmp.{uuid.uuid4().hex}"
        cap = c["settings"].MAX_UPLOAD_MB * 1024 * 1024
        size, too_big = 0, False
        with open(tmp, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > cap:
                    too_big = True
                    break
                f.write(chunk)
        if too_big:
            _unlink(tmp)
            raise HTTPException(413, f"file exceeds {c['settings'].MAX_UPLOAD_MB} MB")

        # hard-link backup keeps dest present while the new bytes land, so a
        # concurrent worker read never sees a missing file
        backup = None
        if os.path.exists(dest):
            backup = f"{dest}.bak.{uuid.uuid4().hex}"
            try:
                os.link(dest, backup)
            except OSError:
                shutil.copy2(dest, backup)
        os.replace(tmp, dest)
        try:
            res = store.replace_document(did, filename)
            if res is None:
                raise HTTPException(404, "unknown document")
        except HTTPException:
            # document vanished under us: nothing to keep
            _unlink(dest)
            if backup:
                _unlink(backup)
            raise
        except Exception:
            # DB write failed after the swap: put the previous bytes back
            if backup:
                os.replace(backup, dest)
            else:
                _unlink(dest)
            raise HTTPException(500, "replace failed, previous file restored")
        if backup:
            _unlink(backup)

    store.log(actor=user.username, action="replace",
              account_id=doc["account_id"], detail=res["filename"])
    return {"job_id": res["job_id"], "status": "queued",
            "document_id": did, "version": res["version"],
            "updated_at": res.get("updated_at")}


@router.delete("/{document_id}", response_model=dict)
def remove(document_id: str, request: Request, user: User = Depends(authed)):
    """Remove a document with its vectors and jobs."""
    c = request.app.state.ctx
    store = c["store"]
    did = _norm_id(document_id)
    doc = store.get_document(did)
    if doc is None:
        raise HTTPException(404, "unknown document")
    _authorize(store, user, doc)

    with _lock_for(did):
        name = store.delete_document(did)
        if name is None:
            raise HTTPException(404, "unknown document")
        dest = os.path.join(UPLOAD_DIR, did)
        _unlink(dest)
        for leftover in glob.glob(f"{dest}.bak.*"):
            _unlink(leftover)

    store.log(actor=user.username, action="delete",
              account_id=doc["account_id"], detail=name)
    return {"deleted": True, "id": did}


@router.get("/{document_id}", response_model=dict)
def view(document_id: str, request: Request, user: User = Depends(authed)):
    """Read-only detail: metadata plus a bounded excerpt of the chunk text."""
    c = request.app.state.ctx
    store = c["store"]
    did = _norm_id(document_id)
    doc = store.get_document(did)
    if doc is None:
        raise HTTPException(404, "unknown document")
    # read rule mirrors list_documents: internal docs are visible to every
    # authenticated user; account docs need membership
    if user.role != "admin" and doc["account_id"] \
            and not store.is_member(user.id, doc["account_id"]):
        raise HTTPException(403, "not assigned to this account")
    content = store.document_content(did)
    if doc.get("uploaded_by") is not None:
        doc = {**doc, "uploaded_by": next(
            (u.username for u in store.list_users()
             if u.id == doc["uploaded_by"]), doc["uploaded_by"])}
    return {**doc, "chunks": content["chunks"],
            "chunk_count": content["total"],
            "truncated": content["total"] > len(content["chunks"])}


@router.get("", response_model=list[dict])
def list_docs(request: Request, account_id: str | None = None,
              internal: bool = False, user: User = Depends(authed)):
    c = request.app.state.ctx
    if account_id is None and not internal:
        raise HTTPException(422, "account_id or internal=true is required")
    if account_id is not None:
        scope = resolve_scope(request, account_id, user)
    else:
        from ..store import Scope
        scope = Scope(user=user, account_id=None, caller="internal",
                      is_admin=(user.role == "admin"))
    return c["store"].list_documents(scope)
