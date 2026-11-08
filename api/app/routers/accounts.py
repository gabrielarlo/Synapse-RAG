from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import admin_only, authed, resolve_scope
from ..schemas import AccountIn, AssignIn
from ..store import User

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[dict])
def list_accounts(request: Request, user: User = Depends(authed)):
    c = request.app.state.ctx
    from ..store import Scope
    scope = Scope(user=user, account_id=None, is_admin=(user.role == "admin"))
    return c["store"].list_accounts(scope)


@router.post("", response_model=dict)
def create_account(body: AccountIn, request: Request,
                   _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    try:
        return c["store"].create_account(body.name)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/{account_id}", response_model=dict)
def get_account(account_id: str, request: Request, user: User = Depends(authed)):
    resolve_scope(request, account_id, user)  # 422/403 enforced here
    c = request.app.state.ctx
    from ..store import Scope
    mine = {a["id"]: a for a in c["store"].list_accounts(
        Scope(user=user, account_id=None, is_admin=(user.role == "admin")))}
    if account_id not in mine:
        raise HTTPException(404, "account not found")
    return mine[account_id]


@router.post("/{account_id}/staff", response_model=dict)
def assign_staff(account_id: str, body: AssignIn, request: Request,
                 _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    if not c["store"].user_exists(body.user_id):
        raise HTTPException(404, "user not found")
    if not c["store"].account_exists(account_id):
        raise HTTPException(404, "account not found")
    c["store"].assign(body.user_id, account_id)
    return {"assigned": True}


@router.delete("/{account_id}/staff/{user_id}", response_model=dict)
def unassign_staff(account_id: str, user_id: str, request: Request,
                   _admin: User = Depends(admin_only)):
    request.app.state.ctx["store"].unassign(user_id, account_id)
    return {"assigned": False}
