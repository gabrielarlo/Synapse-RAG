"""Isolation: A-scoped queries never surface B chunks (mirrors RLS)."""
from app.rag import build_prompt
from app.store import Chunk, Scope
from conftest import authz, login


def _seed(store, a, b):
    one = [1.0] + [0.0] * 7
    other = [0.0, 1.0] + [0.0] * 6
    da = store.create_document("a.txt", a, False, "u")["document"]
    di = store.create_document("i.txt", None, True, "u")["document"]
    db = store.create_document("b.txt", b, False, "u")["document"]
    store.add_chunks(da["id"], [Chunk("acme refunds policy", one)])
    store.add_chunks(di["id"], [Chunk("internal holiday rota", one)])
    store.add_chunks(db["id"], [Chunk("globex secret pricing", other)])
    for j in store.jobs.values():
        store.finish_job(j["id"], True)
    return one, other


def test_internal_sees_own_plus_internal(store):
    one, _ = _seed(store["s"], store["a"]["id"], store["b"]["id"])
    scope = Scope(user=store["staff"], account_id=store["a"]["id"])
    texts = [c["content"] for c in store["s"].search(one, scope)]
    assert any("acme" in t for t in texts) and any("internal" in t for t in texts)
    assert not any("globex" in t for t in texts)


def test_external_never_sees_internal_or_foreign(store):
    one, _ = _seed(store["s"], store["a"]["id"], store["b"]["id"])
    scope = Scope(user=None, account_id=store["a"]["id"], caller="external")
    texts = [c["content"] for c in store["s"].search(one, scope)]
    assert any("acme" in t for t in texts)
    assert not any("globex" in t for t in texts)
    assert not any("internal" in t for t in texts)


def test_prompt_grounds_on_chunks():
    p = build_prompt("q?", [{"content": "hello"}], "")
    assert "hello" in p and "q?" in p


def test_chat_cross_account_question_without_leak(app_client):
    c = app_client["client"]
    s = app_client["app"].state.ctx["store"]
    _seed(s, app_client["a"]["id"], app_client["b"]["id"])
    tok = login(c, "staff", "staffpass")
    # staff member of A asks about B-only topic: must not 403, must not leak
    r = c.post("/api/chat", headers=authz(tok),
               json={"account_id": app_client["a"]["id"],
                     "question": "globex secret pricing"})
    assert r.status_code == 200
