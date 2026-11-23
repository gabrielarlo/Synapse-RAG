import time

from app.security import RateLimiter, make_token, read_token
from conftest import authz, login


def test_login_returns_tokens_and_me(app_client):
    c = app_client["client"]
    tok = login(c, "admin", "adminpass")
    assert tok["token_type"] == "bearer" and tok["access_token"] and tok["refresh_token"]
    r = c.get("/api/auth/me", headers=authz(tok))
    assert r.status_code == 200 and r.json()["role"] == "admin"


def test_refresh_flow(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = c.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert r.status_code == 200 and r.json()["access_token"]


def test_wrong_credentials_401(app_client):
    c = app_client["client"]
    r = c.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_expired_token_401(app_client):
    c = app_client["client"]
    tok = login(c, "admin", "adminpass")
    bad = make_token("test-secret-not-for-prod-use-12345", "admin", "admin", "access",
                     expire_s=-10)
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401
    r = c.get("/api/auth/me", headers=authz(tok))
    assert r.status_code == 200


def test_wrong_kind_token_rejected():
    p = read_token("s", make_token("s", "u", "staff", "refresh", 60), "access")
    assert p is None


def test_rate_limiter_unit():
    rl = RateLimiter()
    for _ in range(3):
        assert rl.allowed("k", 3, 60)[0]
    ok, retry = rl.allowed("k", 3, 60)
    assert not ok and retry > 0


def test_login_throttled_429(app_client):
    c = app_client["client"]
    limiter = app_client["app"].state.ctx["login_limiter"]
    for _ in range(10):  # saturate the window for the test client IP + user
        limiter.allowed("testclient:admin", 10, 60)
    r = c.post("/api/auth/login", json={"username": "admin",
                                        "password": "adminpass"})
    assert r.status_code == 429


def test_cors_headers_present(app_client):
    c = app_client["client"]
    r = c.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") in ("http://localhost:5173", "*")


def test_deactivate_revokes_tokens_login_and_refresh(app_client):
    c = app_client["client"]
    admin_tok = login(c, "admin", "adminpass")
    staff_tok = login(c, "staff", "staffpass")
    sid = app_client["staff"].id

    r = c.get("/api/auth/users", headers=authz(admin_tok))
    assert r.status_code == 200 and all("is_active" in u for u in r.json())
    assert c.post(f"/api/auth/users/{sid}/deactivate",
                  headers=authz(admin_tok)).status_code == 200

    assert c.get("/api/auth/me", headers=authz(staff_tok)).status_code == 403
    assert c.post("/api/auth/refresh",
                  json={"refresh_token": staff_tok["refresh_token"]}).status_code == 403
    assert c.post("/api/auth/login",
                  json={"username": "staff", "password": "staffpass"}).status_code == 403
    assert c.get("/api/auth/me", headers=authz(admin_tok)).status_code == 200

    users = {u["username"]: u for u in c.get(
        "/api/auth/users", headers=authz(admin_tok)).json()}
    assert users["staff"]["is_active"] is False
    assert users["admin"]["is_active"] is True
    assert any(e["action"] == "user_deactivate"
               for e in app_client["s"].audit_query(action="user_deactivate"))


def test_postgres_store_rejects_malformed_user_id_without_db():
    from app.db import PostgresStore

    # A malformed id must be treated as unknown (-> 404), not sent to the UUID
    # column where psycopg raises InvalidTextRepresentation (-> 500).
    store = object.__new__(PostgresStore)
    assert store.deactivate_user("no-such-id") is False


def test_deactivate_guards_self_unknown_and_non_admin(app_client):
    c = app_client["client"]
    admin_tok = login(c, "admin", "adminpass")
    staff_tok = login(c, "staff", "staffpass")

    assert c.post(f"/api/auth/users/{app_client['admin'].id}/deactivate",
                  headers=authz(admin_tok)).status_code == 422
    assert c.post("/api/auth/users/unknown-id/deactivate",
                  headers=authz(admin_tok)).status_code == 404
    assert c.post(f"/api/auth/users/{app_client['staff'].id}/deactivate",
                  headers=authz(staff_tok)).status_code == 403
    assert c.get("/api/auth/me", headers=authz(staff_tok)).status_code == 200
