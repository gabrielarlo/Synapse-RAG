from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import admin_only, authed, check_rate, client_ip
from ..schemas import LoginIn, RefreshIn, TokenOut, UserIn
from ..security import check_password, hash_password, make_token, read_token
from ..store import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens(c: dict, u: User) -> TokenOut:
    s = c["settings"]
    return TokenOut(
        access_token=make_token(s.JWT_SECRET, u.username, u.role, "access",
                                s.JWT_EXPIRE_MIN * 60),
        refresh_token=make_token(s.JWT_SECRET, u.username, u.role, "refresh",
                                 s.REFRESH_EXPIRE_DAYS * 86400))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request):
    c = request.app.state.ctx
    check_rate(c["login_limiter"], f"{client_ip(request)}:{body.username.lower()}",
               c["settings"].LOGIN_RATE_LIMIT, c["settings"].LOGIN_RATE_WINDOW_S)
    u = c["store"].get_user_by_name(body.username)
    if u is None or not check_password(body.password, u.pw_hash):
        raise HTTPException(401, "invalid credentials")
    c["store"].log(actor=u.username, action="login")
    return _tokens(c, u)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, request: Request):
    c = request.app.state.ctx
    p = read_token(c["settings"].JWT_SECRET, body.refresh_token, "refresh")
    if p is None:
        raise HTTPException(401, "invalid or expired refresh token")
    u = c["store"].get_user_by_name(p["sub"])
    if u is None:
        raise HTTPException(401, "unknown user")
    u.role = p["role"]
    return _tokens(c, u)


@router.post("/users", response_model=dict)
def create_user(body: UserIn, request: Request, _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    if body.role not in ("admin", "staff"):
        raise HTTPException(422, "role must be admin or staff")
    try:
        u = c["store"].create_user(body.username, hash_password(body.password),
                                   body.role, body.display_name)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"id": u.id, "username": u.username, "role": u.role,
            "display_name": u.display_name}


@router.get("/users", response_model=list[dict])
def list_users(request: Request, _admin: User = Depends(admin_only)):
    c = request.app.state.ctx
    return [{"id": u.id, "username": u.username, "role": u.role,
             "display_name": u.display_name} for u in c["store"].list_users()]


@router.get("/me", response_model=dict)
def me(user: User = Depends(authed)):
    return {"id": user.id, "username": user.username, "role": user.role,
            "display_name": user.display_name}
