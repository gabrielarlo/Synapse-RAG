from app.main import create_app
from app.ollama import FakeOllama
from app.sessions import SessionStore
from app.triage import parse_triage
from conftest import authz, login
from fastapi.testclient import TestClient


def test_parse_valid():
    t = parse_triage('{"category": "billing", "escalate": true,'
                     ' "department": "finance"}')
    assert (t.category, t.escalate, t.department) == ("billing", True, "finance")


def test_parse_drift_falls_back():
    t = parse_triage("Sure thing! I think this is urgent, trust me.")
    assert (t.category, t.escalate, t.department) == ("general", False, None)


def test_escalation_labels_and_logs(app_client):
    store = app_client["s"]
    app = create_app(store=store, sessions=SessionStore(":memory:"),
                     ollama=FakeOllama({"category": "complaint", "escalate": True,
                                        "department": "billing"}))
    with TestClient(app) as c:
        tok = login(c, "staff", "staffpass")
        r = c.post("/api/chat", headers=authz(tok),
                   json={"account_id": app_client["a"]["id"],
                         "question": "I want a refund NOW"})
        body = r.json()
        assert r.status_code == 200 and body["escalated"]
        assert body["department"] == "billing"
        assert body["answer"].startswith("[Escalated to billing]")
        assert any(e["action"] == "escalation" for e in store.events)


def test_audit_prefix_skips_triage_and_vectors(app_client):
    store = app_client["s"]
    fake = FakeOllama({"category": "x", "escalate": True, "department": "y"})
    app = create_app(store=store, sessions=SessionStore(":memory:"), ollama=fake)
    with TestClient(app) as c:
        tok = login(c, "admin", "adminpass")
        r = c.post("/api/chat", headers=authz(tok),
                   json={"account_id": app_client["a"]["id"],
                         "question": "audit: how many logins today?"})
        assert r.status_code == 200 and r.json()["category"] == "audit"
        assert "decide" not in fake.calls  # triage never ran
        assert "embed" not in fake.calls  # retrieval never ran


def test_decide_systemone_mapping_and_safe_fallback():
    from app.ollama import Ollama

    seen = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"answers": {
                "category": {"type": "choice", "choice": "billing"},
                "escalate": {"type": "noul", "noul": 0.77},
                "department": {"type": "choice", "choice": "billing"}}}

    class Http:
        def post(self, url, json=None):
            seen["url"] = url
            seen.update(json)
            return Resp()

    o = Ollama("http://x", "g", "e", "d1:2b")
    o._http = Http()
    t = parse_triage(o.decide("I want a refund NOW"))
    assert (t.category, t.escalate, t.department) == ("billing", True, "billing")
    assert seen["url"].endswith("/v1/systemone") and seen["model"] == "d1:2b"

    # malformed 200 shape falls back instead of raising
    class BadResp(Resp):
        def json(self):
            return {"unexpected": True}

    class BadHttp(Http):
        def post(self, url, json=None):
            return BadResp()

    o._http = BadHttp()
    t = parse_triage(o.decide("hi"))
    assert (t.category, t.escalate, t.department) == ("general", False, None)
