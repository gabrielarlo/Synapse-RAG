from conftest import authz, login


def test_staff_sees_only_assigned(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    names = [a["name"] for a in c.get("/api/accounts",
                                      headers=authz(tok)).json()]
    assert names == ["Acme"]


def test_admin_sees_all(app_client):
    c = app_client["client"]
    tok = login(c, "admin", "adminpass")
    names = sorted(a["name"] for a in c.get("/api/accounts",
                                            headers=authz(tok)).json())
    assert names == ["Acme", "Globex"]


def test_unassigned_account_403(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    b = app_client["b"]["id"]
    r = c.get(f"/api/accounts/{b}", headers=authz(tok))
    assert r.status_code == 403


def test_missing_account_id_422(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = c.get("/api/documents", headers=authz(tok))
    assert r.status_code == 422
    r = c.post("/api/documents", headers=authz(tok),
               files={"file": ("x.txt", b"hi")})
    assert r.status_code == 422


def test_assign_and_revoke(app_client):
    c = app_client["client"]
    admin, staff_id = login(c, "admin", "adminpass"), app_client["staff"].id
    b = app_client["b"]["id"]
    r = c.post(f"/api/accounts/{b}/staff", headers=authz(admin),
               json={"user_id": staff_id})
    assert r.status_code == 200
    stok = login(c, "staff", "staffpass")
    assert sorted(a["name"] for a in c.get("/api/accounts",
                                           headers=authz(stok)).json()) == ["Acme", "Globex"]
    r = c.delete(f"/api/accounts/{b}/staff/{staff_id}", headers=authz(admin))
    assert r.status_code == 200
    stok = login(c, "staff", "staffpass")
    r = c.get(f"/api/accounts/{b}", headers=authz(stok))
    assert r.status_code == 403


def test_non_admin_cannot_create_user(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = c.post("/api/auth/users", headers=authz(tok),
               json={"username": "x", "password": "yyyy", "role": "staff"})
    assert r.status_code == 403


def test_assign_unknown_user_or_account_404(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    r = c.post(f"/api/accounts/{app_client['a']['id']}/staff", headers=authz(admin),
               json={"user_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404
    r = c.post("/api/accounts/00000000-0000-0000-0000-000000000000/staff",
               headers=authz(admin),
               json={"user_id": app_client["staff"].id})
    assert r.status_code == 404


def test_foreign_session_chat_403(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    a = app_client["a"]["id"]
    b = app_client["b"]["id"]
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": a, "question": "hi"})
    sid = r.json()["session_id"]
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": b, "question": "hijack?", "session_id": sid})
    assert r.status_code == 403
