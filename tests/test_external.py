from app.security import check_password
from conftest import authz, login


def _issue(c, admin_tok, account_id):
    r = c.post(f"/api/accounts/{account_id}/credentials", headers=authz(admin_tok))
    assert r.status_code == 200, r.text
    return r.json()


def test_issue_once_only_and_auth(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    cred = _issue(c, admin, app_client["a"]["id"])
    assert cred["secret"]
    stored = app_client["s"].get_credential(cred["key_id"])
    assert stored["secret_hash"] != cred["secret"]  # hashed at rest
    assert check_password(cred["secret"], stored["secret_hash"])
    r = c.post("/ext/faq", headers={"X-API-Key": cred["key_id"],
                                    "X-API-Secret": cred["secret"]},
               json={"question": " refunds?"})
    assert r.status_code == 200 and r.json()["category"] == "external_faq"


def test_invalid_and_revoked_401(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    cred = _issue(c, admin, app_client["a"]["id"])
    bad = {"X-API-Key": cred["key_id"], "X-API-Secret": "wrong"}
    assert c.post("/ext/faq", headers=bad, json={"question": "x"}).status_code == 401
    assert c.post("/ext/faq", headers={"X-API-Key": "nope", "X-API-Secret": "x"},
                  json={"question": "x"}).status_code == 401
    c.delete(f"/api/credentials/{cred['key_id']}", headers=authz(admin))
    good = {"X-API-Key": cred["key_id"], "X-API-Secret": cred["secret"]}
    assert c.post("/ext/faq", headers=good, json={"question": "x"}).status_code == 401


def test_rotation_invalidates_old(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    cred = _issue(c, admin, app_client["a"]["id"])
    r = c.post(f"/api/credentials/{cred['key_id']}/rotate", headers=authz(admin))
    assert r.status_code == 200
    new = r.json()["secret"]
    old_h = {"X-API-Key": cred["key_id"], "X-API-Secret": cred["secret"]}
    new_h = {"X-API-Key": cred["key_id"], "X-API-Secret": new}
    assert c.post("/ext/faq", headers=old_h, json={"question": "x"}).status_code == 401
    assert c.post("/ext/faq", headers=new_h, json={"question": "x"}).status_code == 200


def test_audit_prefix_is_literal_text(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    cred = _issue(c, admin, app_client["a"]["id"])
    r = c.post("/ext/faq", headers={"X-API-Key": cred["key_id"],
                                    "X-API-Secret": cred["secret"]},
               json={"question": "audit: how many logins today?"})
    assert r.status_code == 200 and r.json()["category"] == "external_faq"


def test_faq_throttled_429(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    cred = _issue(c, admin, app_client["a"]["id"])
    limiter = app_client["app"].state.ctx["faq_limiter"]
    for _ in range(60):
        limiter.allowed(f"testclient:{cred['key_id']}", 60, 60)
    r = c.post("/ext/faq", headers={"X-API-Key": cred["key_id"],
                                    "X-API-Secret": cred["secret"]},
               json={"question": "x"})
    assert r.status_code == 429
