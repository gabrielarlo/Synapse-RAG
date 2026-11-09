import pytest

from app.main import create_app
from app.ollama import FakeOllama
from app.sessions import SessionStore
from app.store import InMemoryStore
from conftest import authz, login
from fastapi.testclient import TestClient


def test_context_within_window():
    s = SessionStore(":memory:")
    sid, expired, ctx = s.user_message(None, "u", "a", "I like cats", now=1000.0)
    assert not expired and ctx == ""
    s.assistant_message(sid, "noted")
    _, expired2, ctx2 = s.user_message(sid, "u", "a", "what else?", now=2000.0)
    assert not expired2 and "cats" in ctx2


def test_expiry_wipes_and_flags():
    s = SessionStore(":memory:", ttl_s=60)
    sid, _, _ = s.user_message(None, "u", "a", "secret topic", now=1000.0)
    _, expired, ctx = s.user_message(sid, "u", "a", "follow up", now=2000.0)
    assert expired and ctx == ""


def test_boundary_not_expired():
    s = SessionStore(":memory:", ttl_s=60)
    sid, _, _ = s.user_message(None, "u", "a", "x", now=1000.0)
    _, expired, _ = s.user_message(sid, "u", "a", "y", now=1060.0)
    assert not expired  # strictly-more-than TTL expires


def test_cross_account_rejected():
    s = SessionStore(":memory:")
    sid, _, _ = s.user_message(None, "u", "a", "x", now=1000.0)
    with pytest.raises(PermissionError):
        s.user_message(sid, "u", "b", "y", now=1001.0)


def test_assistant_message_does_not_touch():
    s = SessionStore(":memory:", ttl_s=60)
    sid, _, _ = s.user_message(None, "u", "a", "x", now=1000.0)
    s.assistant_message(sid, "reply")  # must not move last_active
    _, expired, _ = s.user_message(sid, "u", "a", "y", now=1059.0)
    assert not expired


def test_chat_session_reuse_and_expiry_notice(app_client):
    # dedicated zero-TTL app: every second message is expired
    store2 = app_client["s"]
    app2 = create_app(store=store2, sessions=SessionStore(":memory:", ttl_s=0),
                      ollama=FakeOllama())
    with TestClient(app2) as c2:
        tok = login(c2, "staff", "staffpass")
        a = app_client["a"]["id"]
        r1 = c2.post("/api/chat", headers=authz(tok),
                     json={"account_id": a, "question": "hello"})
        assert r1.status_code == 200 and not r1.json()["session_expired"]
        sid = r1.json()["session_id"]
        r2 = c2.post("/api/chat", headers=authz(tok),
                     json={"account_id": a, "question": "again",
                           "session_id": sid})
        body = r2.json()
        assert body["session_expired"] and "expired" in body["answer"]


def test_context_returns_latest_turns_first():
    from app.sessions import SessionStore as SS
    s = SS(":memory:")
    sid, _, _ = s.user_message(None, "u", "a", "turn0", now=1000.0)
    for i in range(1, 9):
        s.assistant_message(sid, f"reply{i}")
        s.user_message(sid, "u", "a", f"turn{i}", now=1000.0 + i)
    _, _, ctx = s.user_message(sid, "u", "a", "latest?", now=2000.0)
    assert "turn0" not in ctx and "turn8" in ctx


def test_stale_claimed_job_requeued(store):
    import time
    from app.store import CLAIM_STALE_S
    s = store["s"]
    doc = s.create_document("x.txt", store["a"]["id"], False, "u")
    jid = [j for j in s.jobs.values()
           if j["document_id"] == doc["document"]["id"]][0]["id"]
    s.jobs[jid]["status"] = "claimed"
    s.jobs[jid]["updated_at"] = time.time() - CLAIM_STALE_S - 1
    got = s.claim_job()
    assert got is not None and got["id"] == jid


def test_session_history_roundtrip_and_ownership(app_client):
    c = app_client["client"]
    staff = login(c, "staff", "staffpass")
    admin = login(c, "admin", "adminpass")
    a = app_client["a"]["id"]
    sid = c.post("/api/chat", headers=authz(staff),
                 json={"account_id": a, "question": "hello"}).json()["session_id"]

    r = c.get(f"/api/chat/sessions/{sid}/history", headers=authz(staff))
    assert r.status_code == 200, r.text
    turns = r.json()["turns"]
    assert [(t["role"], t["content"]) for t in turns] == [
        ("user", "hello"), ("assistant", " grounded answer from context")]
    assert all(t["ts"] for t in turns)  # reload restore shows time…
    assert turns[1]["category"] == "general"  # …and category
    assert turns[1]["escalated"] is False and turns[1]["department"] is None

    # unknown session 404s; another user's session 403s
    assert c.get("/api/chat/sessions/sess_nope/history",
                 headers=authz(staff)).status_code == 404
    assert c.get(f"/api/chat/sessions/{sid}/history",
                 headers=authz(admin)).status_code == 403


def test_today_is_manila_day():
    from datetime import datetime

    from app.audit import _APP_TZ, _today
    assert _today() == datetime.now(_APP_TZ).date().isoformat()
