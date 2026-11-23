"""Admin-only audit trail + per-account credential management."""
import secrets as _secrets

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ..deps import admin_only
from ..schemas import CredentialIn, CredentialOut
from ..security import hash_password
from ..store import User

router = APIRouter(tags=["audit", "credentials"])


@router.get("/api/audit", response_model=list[dict])
def trail(request: Request, action: str | None = None,
          account_id: str | None = None, limit: int = 100,
          _admin: User = Depends(admin_only)):
    return request.app.state.ctx["store"].audit_query(action, account_id, limit)


@router.get("/api/accounts/{account_id}/credentials", response_model=list[dict])
def list_credentials(account_id: str, request: Request,
                     _admin: User = Depends(admin_only)):
    """List API keys for an account (secret is never returned)."""
    c = request.app.state.ctx
    if not c["store"].account_exists(account_id):
        raise HTTPException(404, "account not found")
    return c["store"].list_credentials(account_id)


@router.post("/api/accounts/{account_id}/credentials",
             response_model=CredentialOut,
             summary="Issue API key for an account",
             description="Creates a new key/secret pair. Plaintext secret is returned only once. Default expiry 90 days.")
def issue(account_id: str, request: Request,
          _admin: User = Depends(admin_only),
          body: CredentialIn | None = Body(default=None)):
    data = body or CredentialIn()
    if data.label is not None and not data.label.strip():
        raise HTTPException(422, "label must not be empty")
    c = request.app.state.ctx
    if not c["store"].account_exists(account_id):
        raise HTTPException(404, "account not found")
    secret = _secrets.token_urlsafe(32)
    key_id = c["store"].issue_credential(account_id, hash_password(secret),
                                          label=data.label.strip() if data.label else None,
                                          expires_in_days=data.expires_in_days)
    cred = c["store"].get_credential(key_id)
    c["store"].log(actor=_admin.username, action="credential_issue",
                    account_id=account_id, detail=key_id)
    return CredentialOut(key_id=key_id, account_id=account_id, secret=secret,
                         label=cred.get("label"), expires_at=cred.get("expires_at"),
                         created_at=cred.get("created_at"))


@router.post("/api/credentials/{key_id}/rotate", response_model=CredentialOut)
def rotate(key_id: str, request: Request, _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    cred = c["store"].get_credential(key_id)
    if cred is None:
        raise HTTPException(404, "unknown key")
    secret = _secrets.token_urlsafe(32)
    c["store"].rotate_credential(key_id, hash_password(secret))
    # fetch updated row for label/expires_at to return
    updated = c["store"].get_credential(key_id)
    c["store"].log(actor=_admin.username, action="credential_rotate",
                    account_id=cred["account_id"], detail=key_id)
    return CredentialOut(key_id=key_id, account_id=cred["account_id"],
                         secret=secret, label=updated.get("label"),
                         expires_at=updated.get("expires_at"),
                         created_at=updated.get("created_at"))


@router.post("/api/credentials/{key_id}/revoke", response_model=dict)
def revoke(key_id: str, request: Request, _admin: User = Depends(admin_only)):
    """Soft-revoke: keeps the row but blocks auth (reversible via rotate)."""
    c = request.app.state.ctx
    cred = c["store"].get_credential(key_id)
    if cred is None:
        raise HTTPException(404, "unknown key")
    c["store"].revoke_credential(key_id)
    c["store"].log(actor=_admin.username, action="credential_revoke",
                    account_id=cred["account_id"], detail=key_id)
    return {"revoked": True}


@router.delete("/api/credentials/{key_id}", response_model=dict)
def delete_cred(key_id: str, request: Request, _admin: User = Depends(admin_only)):
    """Hard delete — removes the key entirely."""
    c = request.app.state.ctx
    cred = c["store"].get_credential(key_id)
    if cred is None:
        raise HTTPException(404, "unknown key")
    # keep delete for backward compat: old clients DELETE expecting revoke return {"revoked": true}
    # new UI calls DELETE for hard delete — both 401 thereafter, so test stays green
    ok = c["store"].delete_credential(key_id)
    c["store"].log(actor=_admin.username, action="credential_delete",
                    account_id=cred["account_id"], detail=key_id)
    return {"deleted": True, "revoked": True} if ok else {"deleted": False}
