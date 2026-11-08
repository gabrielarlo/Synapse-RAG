"""Shared request dependencies: auth, scope resolution, rate limits."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from .security import read_token
from .store import Scope, User


def authed(request: Request, authorization: str = Header(default="")) -> User:
    c = request.app.state.ctx
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    p = read_token(c["settings"].JWT_SECRET, authorization[7:], "access")
    if p is None:
        raise HTTPException(401, "invalid or expired token")
    u = c["store"].get_user_by_name(p["sub"])
    if u is None:
        raise HTTPException(401, "unknown user")
    u.role = p["role"]
    return u


def admin_only(user: User = Depends(authed)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "admin only")
    return user


def resolve_scope(request: Request, account_id: str | None,
                  user: User) -> Scope:
    """Explicit account_id + membership check; admins bypass membership."""
    c = request.app.state.ctx
    if not account_id:
        raise HTTPException(422, "account_id is required")
    if user.role != "admin" and not c["store"].is_member(user.id, account_id):
        raise HTTPException(403, "not assigned to this account")
    return Scope(user=user, account_id=account_id, caller="internal",
                 is_admin=(user.role == "admin"))


def client_ip(request: Request) -> str:
    # Behind the compose nginx proxy the peer is always the proxy; prefer the
    # forwarded client. Direct API exposure lets callers spoof XFF, so bucket
    # keys below always pair the IP with a username or key id.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or "?"
    return request.client.host if request.client else "?"


def check_rate(limiter, key: str, limit: int, window_s: int) -> None:
    ok, retry = limiter.allowed(key, limit, window_s)
    if not ok:
        raise HTTPException(429, f"rate limited, retry in {retry}s")
