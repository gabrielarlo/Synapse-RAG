from app.ollama import FakeOllama
from conftest import authz, login


def _upload(c, tok, account_id, name="f.txt", body=b"hello world"):
    return c.post(f"/api/documents?account_id={account_id}", headers=authz(tok),
                  files={"file": (name, body)})


def test_audit_trail_admin_only(app_client):
    c = app_client["client"]
    stok = login(c, "staff", "staffpass")
    assert c.get("/api/audit", headers=authz(stok)).status_code == 403
    admin = login(c, "admin", "adminpass")
    _upload(c, admin, app_client["a"]["id"])
    r = c.get("/api/audit?action=upload", headers=authz(admin))
    assert r.status_code == 200 and len(r.json()) == 1
    assert r.json()[0]["action"] == "upload"


def test_staff_audit_prefix_403(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = c.post("/api/chat", headers=authz(tok),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: how many logins today?"})
    assert r.status_code == 403


def test_admin_audit_count_and_refusal(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    staff = login(c, "staff", "staffpass")
    _upload(c, admin, app_client["a"]["id"], "u1.txt")
    _upload(c, staff, app_client["a"]["id"], "u2.txt")
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: how many users do upload files today?"})
    assert r.status_code == 200
    assert "2" in r.json()["answer"] and "today" in r.json()["answer"].lower()
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: how many uploads happened today?"})
    assert r.status_code == 200 and "2" in r.json()["answer"]
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: uploads this day"})
    assert r.status_code == 200 and "2" in r.json()["answer"]
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: uploads per day"})
    assert r.status_code == 200 and "2" in r.json()["answer"]
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: what is the meaning of life?"})
    assert r.status_code == 200 and "can only answer" in r.json()["answer"]


def test_audit_manila_day_and_account_scope(app_client):
    from datetime import datetime, time, timezone

    from app.audit import _APP_TZ, answer_audit
    s = app_client["s"]
    a, b = app_client["a"]["id"], app_client["b"]["id"]
    # 00:30 Manila today == yesterday 16:30 UTC: old UTC-prefix logic missed it.
    today_manila = datetime.now(_APP_TZ).date()
    ts = datetime.combine(today_manila, time(0, 30), tzinfo=_APP_TZ) \
        .astimezone(timezone.utc).isoformat()
    s.events.append({"ts": ts, "actor": "admin", "action": "upload",
                     "account_id": b, "detail": None})
    s.log(actor="admin", action="login")  # logins carry no account
    ok, text = answer_audit("audit: uploads today", s, b)
    assert ok and "Asia/Manila" in text and ": 1." in text
    ok, text = answer_audit("audit: uploads today", s, a)
    assert ok and ": 0." in text  # other account's upload is out of scope
    ok, text = answer_audit("audit: how many logins today?", s, b)
    assert ok and ": 1." in text  # platform-wide, not scoped to 0


def test_audit_session_history_roundtrip(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    staff = login(c, "staff", "staffpass")
    r = c.post("/api/chat", headers=authz(admin),
               json={"account_id": app_client["a"]["id"],
                     "question": "audit: how many logins today?"})
    assert r.status_code == 200 and r.json()["session_id"]
    sid = r.json()["session_id"]
    h = c.get(f"/api/chat/sessions/{sid}/history", headers=authz(admin))
    assert h.status_code == 200
    turns = h.json()["turns"]
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[0]["content"] == "audit: how many logins today?"
    assert turns[1]["content"].startswith("Logins today (Asia/Manila)")
    assert all(t["ts"] for t in turns)
    assert turns[1]["category"] == "audit"
    assert c.get(f"/api/chat/sessions/{sid}/history",
                 headers=authz(staff)).status_code == 403


def test_authorized_upload_returns_job(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = _upload(c, tok, app_client["a"]["id"])
    assert r.status_code == 200 and r.json()["status"] == "queued"
    assert r.json()["job_id"]


def test_unauthorized_upload_403(app_client):
    c = app_client["client"]
    tok = login(c, "staff", "staffpass")
    r = _upload(c, tok, app_client["b"]["id"])
    assert r.status_code == 403


def test_failed_ingestion_marks_failed(app_client, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "worker", "worker/worker.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    store = app_client["s"]
    doc = store.create_document("bad.txt", app_client["a"]["id"], False, "u")
    with open(tmp_path / doc["document"]["id"], "wb") as f:
        f.write(b"data")
    worker.UPLOAD_DIR = str(tmp_path)

    class Boom(FakeOllama):
        def embed(self, texts):
            raise RuntimeError("ollama down")

    worker.run_once(store, Boom())
    assert store.documents[doc["document"]["id"]]["status"] == "failed"
    assert "ollama down" in (store.documents[doc["document"]["id"]]["error"] or "")


def test_worker_happy_path(app_client, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "worker", "worker/worker.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    store = app_client["s"]
    doc = store.create_document("ok.txt", app_client["a"]["id"], False, "u")
    with open(tmp_path / doc["document"]["id"], "wb") as f:
        f.write(b"acme refund policy text here")
    worker.UPLOAD_DIR = str(tmp_path)
    assert worker.run_once(store, FakeOllama()) is True
    assert store.documents[doc["document"]["id"]]["status"] == "ready"
    assert any(e["action"] == "ingest" for e in store.events)
    assert worker.run_once(store, FakeOllama()) is False  # queue drained


def test_upload_over_cap_413(app_client):
    c = app_client["client"]
    app_client["app"].state.ctx["settings"].MAX_UPLOAD_MB = 0
    tok = login(c, "staff", "staffpass")
    r = c.post(f"/api/documents?account_id={app_client['a']['id']}",
               headers=authz(tok), files={"file": ("big.txt", b"x" * 16)})
    assert r.status_code == 413


def test_ollama_down_503(app_client):
    import httpx
    from app.main import create_app
    from app.ollama import FakeOllama
    from app.sessions import SessionStore
    from fastapi.testclient import TestClient

    class Down(FakeOllama):
        def decide(self, question):
            raise httpx.ConnectError("ollama gone")

    app = create_app(store=app_client["s"], sessions=SessionStore(":memory:"),
                     ollama=Down())
    with TestClient(app) as c2:
        tok = login(c2, "staff", "staffpass")
        r = c2.post("/api/chat", headers=authz(tok),
                    json={"account_id": app_client["a"]["id"], "question": "hi"})
        assert r.status_code == 503
