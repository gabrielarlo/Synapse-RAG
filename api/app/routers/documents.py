from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ..deps import authed, resolve_scope
from ..store import User

import os

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")

router = APIRouter(prefix="/api/documents", tags=["documents"])


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
