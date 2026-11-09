"""Live end-to-end: real PG+pgvector, real Ollama (gen/embed/decision).
Run: TEST_DATABASE_URL=postgresql://synapse@/pg-socket-dir/synapse_e2e_meta ...
Actually: TEST_PG_SOCKDIR=<cluster socket dir> TEST_PG_PORT=<port>.
Skipped unless both TEST_PG_SOCKDIR and TEST_LIVE_OLLAMA=1 are set.
Covers tasks 3.2 (chunks RLS), 4.2, 5.1-5.3, 6.2, 7.2, 8.2 against real infra.
"""
import os
import uuid

import pytest

SOCKDIR = os.environ.get("TEST_PG_SOCKDIR", "")
PORT = os.environ.get("TEST_PG_PORT", "54399")
LIVE = bool(SOCKDIR) and os.environ.get("TEST_LIVE_OLLAMA") == "1"

pytestmark = pytest.mark.skipif(not LIVE, reason="needs live PG + Ollama")


def _dsn(db, user="synapse"):
    return f"host={SOCKDIR} port={PORT} dbname={db} user={user}"


@pytest.fixture(scope="module")
def live():
    import psycopg
    from fastapi.testclient import TestClient

    from app.db import PostgresStore
    from app.main import create_app
    from app.ollama import Ollama
    from app.security import hash_password
    from app.sessions import SessionStore

    dbname = f"e2e_{uuid.uuid4().hex[:8]}"
    admin = psycopg.connect(host=SOCKDIR, port=PORT, dbname="postgres",
                            user="synapse", autocommit=True)
    admin.execute(f'CREATE DATABASE "{dbname}"')
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migdir = os.path.join(root, "infra", "migrations")
        m = psycopg.connect(_dsn(dbname), autocommit=True)
        for name in sorted(os.listdir(migdir)):
            if name.endswith(".sql"):
                with open(os.path.join(migdir, name)) as f:
                    m.execute(f.read())
        m.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles"
                  " WHERE rolname='app') THEN CREATE ROLE app LOGIN; END IF; END $$;"
                  " GRANT CONNECT ON DATABASE"
                  f' "{dbname}" TO app; GRANT USAGE ON SCHEMA public TO app;'
                  " GRANT ALL ON ALL TABLES IN SCHEMA public TO app;"
                  " ALTER DEFAULT PRIVILEGES IN SCHEMA public"
                  " GRANT ALL ON TABLES TO app;")
        m.close()

        store = PostgresStore(_dsn(dbname, "app"))  # non-superuser: RLS applies
        ollama = Ollama("http://localhost:11434", "llama3.2:3b",
                        "nomic-embed-text:latest", "llama3.2:3b", timeout_s=300.0)
        import tempfile
        sessions = SessionStore(tempfile.mktemp(suffix=".db"), ttl_s=1800)
        app = create_app(store=store, sessions=sessions, ollama=ollama)

        admin_u = store.create_user("admin", hash_password("adminpass"), "admin")
        staff_u = store.create_user("staff", hash_password("staffpass"), "staff")
        a = store.create_account("Acme")
        b = store.create_account("Globex")
        store.assign(staff_u.id, a["id"])
        with TestClient(app) as client:
            yield {"client": client, "app": app, "store": store,
                   "admin": admin_u, "staff": staff_u, "a": a, "b": b}
    finally:
        admin.execute(f'DROP DATABASE "{dbname}" WITH (FORCE)')
        admin.close()


def _login(client, u, p):
    r = client.post("/api/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_e2e_full_flow(live, tmp_path, monkeypatch):
    import worker.worker as worker

    c, store = live["client"], live["store"]
    a, b = live["a"]["id"], live["b"]["id"]
    ah, sh = _login(c, "admin", "adminpass"), _login(c, "staff", "staffpass")
    monkeypatch.setattr("app.routers.documents.UPLOAD_DIR", str(tmp_path))
    worker.UPLOAD_DIR = str(tmp_path)

    # upload Acme doc + internal doc, ingest with real embeddings
    for acct, name, text in ((a, "acme.txt", "Acme refunds take five business days."),
                             (None, "hol.txt", "Internal: office closes on Founders Day.")):
        q = f"account_id={acct}" if acct else "internal=true"
        r = c.post(f"/api/documents?{q}", headers=sh, files={"file": (name, text.encode())})
        assert r.status_code == 200, r.text
        did = r.json()["document_id"]
        with open(tmp_path / did, "wb") as f:
            f.write(text.encode())
        assert worker.run_once(store, live["app"].state.ctx["ollama"]) is True
    assert worker.run_once(store, live["app"].state.ctx["ollama"]) is False

    # RLS on chunks: internal/A sees Acme+internal, external/A excludes internal
    from app.store import Scope
    vec = live["app"].state.ctx["ollama"].embed(["refunds"])[0]
    assert len(vec) == 768
    got_in = {x["content"] for x in store.search(vec, Scope(None, a, "internal", False))}
    assert any("Acme" in t for t in got_in) and any("Founders" in t for t in got_in)
    got_ex = {x["content"] for x in store.search(vec, Scope(None, a, "external", False))}
    assert any("Acme" in t for t in got_ex) and not any("Founders" in t for t in got_ex)

    # document_content: real SQL ordering, cap and total count
    content = store.document_content(did, limit=1)
    assert len(content["chunks"]) == 1 and content["total"] >= 1

    # staff asks: triage + retrieval + generation live
    r = c.post("/api/chat", headers=sh,
               json={"account_id": a, "question": "How long do Acme refunds take?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"].strip() and body["session_id"] and body["category"]
    # follow-up reuses session
    r2 = c.post("/api/chat", headers=sh,
                json={"account_id": a, "question": "And who approves them?",
                      "session_id": body["session_id"]})
    assert r2.status_code == 200 and r2.json()["session_id"] == body["session_id"]

    # external FAQ live
    r = c.post(f"/api/accounts/{a}/credentials", headers=ah)
    cred = r.json()
    h = {"X-API-Key": cred["key_id"], "X-API-Secret": cred["secret"]}
    r = c.post("/ext/faq", headers=h, json={"question": "How long do refunds take?"})
    assert r.status_code == 200 and r.json()["answer"].strip()

    # staff assignment endpoint on Postgres (regression: used to 500)
    staff_id = live["staff"].id
    r = c.post(f"/api/accounts/{b}/staff", headers=ah,
               json={"user_id": staff_id})
    assert r.status_code == 200, r.text
    r = c.post("/api/accounts/00000000-0000-0000-0000-000000000000/staff",
               headers=ah, json={"user_id": staff_id})
    assert r.status_code == 404
    r = c.post(f"/api/accounts/{a}/staff", headers=ah,
               json={"user_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404

    # admin audit question over real events
    r = c.post("/api/chat", headers=ah,
               json={"account_id": a,
                     "question": "audit: how many users do upload files today?"})
    assert r.status_code == 200 and "today" in r.json()["answer"].lower()
