"""JWT auth, password hashing, in-memory sliding-window rate limiter."""
from __future__ import annotations

import time
from collections import defaultdict, deque

import bcrypt
import jwt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(secret: str, sub: str, role: str, kind: str,
               expire_s: int) -> str:
    now = int(time.time())
    return jwt.encode({"sub": sub, "role": role, "kind": kind,
                       "iat": now, "exp": now + expire_s}, secret, algorithm="HS256")


def read_token(secret: str, token: str, kind: str) -> dict | None:
    try:
        p = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return p if p.get("kind") == kind else None


class RateLimiter:
    """Sliding-window limiter: allow(limit) calls per window_s per key."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        now = time.time()
        q = self._hits[key]
        while q and q[0] <= now - window_s:
            q.popleft()
        if len(q) >= limit:
            return False, int(q[0] + window_s - now) + 1
        q.append(now)
        if len(self._hits) > 10000:  # bound memory: drop fully-expired buckets
            for k in [k for k, v in self._hits.items()
                      if not v or v[-1] <= now - window_s]:
                del self._hits[k]
        return True, 0
