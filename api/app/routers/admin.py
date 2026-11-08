"""Admin-only audit trail + per-account credential management."""
import secrets as _secrets

from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import admin_only
from ..schemas import CredentialOut
from ..security import hash_password
from ..store import User

router = APIRouter(tags=["audit"])


@router.get("/api/audit", response_model=list[dict])
def trail(request: Request, action: str | None = None,
          account_id: str | None = None, limit: int = 100,
          _admin: User = Depends(admin_only)):
    return request.app.state.ctx["store"].audit_query(action, account_id, limit)


@router.post("/api/accounts/{account_id}/credentials",
             response_model=CredentialOut)
def issue(account_id: str, request: Request,
          _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    secret = _secrets.token_urlsafe(32)
    key_id = c["store"].issue_credential(account_id, hash_password(secret))
    c["store"].log(actor=_admin.username, action="credential_issue",
                    account_id=account_id, detail=key_id)
    return CredentialOut(key_id=key_id, account_id=account_id, secret=secret)


@router.post("/api/credentials/{key_id}/rotate", response_model=CredentialOut)
def rotate(key_id: str, request: Request, _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    cred = c["store"].get_credential(key_id)
    if cred is None:
        raise HTTPException(404, "unknown key")
    secret = _secrets.token_urlsafe(32)
    c["store"].rotate_credential(key_id, hash_password(secret))
    c["store"].log(actor=_admin.username, action="credential_rotate",
                    account_id=cred["account_id"], detail=key_id)
    return CredentialOut(key_id=key_id, account_id=cred["account_id"],
                         secret=secret)


@router.delete("/api/credentials/{key_id}", response_model=dict)
def revoke(key_id: str, request: Request, _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    cred = c["store"].get_credential(key_id)
    if cred is None:
        raise HTTPException(404, "unknown key")
    c["store"].revoke_credential(key_id)
    c["store"].log(actor=_admin.username, action="credential_revoke",
                    account_id=cred["account_id"], detail=key_id)
    return {"revoked": True}
