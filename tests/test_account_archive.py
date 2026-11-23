"""Reversible account archive: authz, real state change, and cascade to the
account's documents/chunks/jobs. Hermetic — InMemoryStore, no live PG/Ollama."""
from app.store import Chunk, Scope
from conftest import authz, login


def _archive(c, tok, aid, path="archive"):
    return c.post(f"/api/accounts/{aid}/{path}", headers=authz(tok))


def _upload(c, tok, aid, name):
    r = c.post("/api/documents", headers=authz(tok),
               params={"account_id": aid},
               files={"file": (name, b"hello world")})
    assert r.status_code == 200, r.text
    return r.json()["document_id"]


def _issue(c, admin_tok, aid):
    r = c.post(f"/api/accounts/{aid}/credentials", headers=authz(admin_tok))
    assert r.status_code == 200, r.text
    return r.json()


def test_archive_requires_admin_and_known_account(app_client):
    c = app_client["client"]
    admin, staff = login(c, "admin", "adminpass"), login(c, "staff", "staffpass")
    aid = app_client["a"]["id"]
    assert _archive(c, staff, aid).status_code == 403
    assert not app_client["s"].is_archived(aid)
    assert _archive(c, admin, "not-a-uuid").status_code == 404
    assert _archive(c, admin, aid).status_code == 200
    assert _archive(c, admin, aid, "unarchive").status_code == 200


def test_flag_persists_and_list_visibility_matches_role(app_client):
    c = app_client["client"]
    admin, staff = login(c, "admin", "adminpass"), login(c, "staff", "staffpass")
    aid, other = app_client["a"]["id"], app_client["b"]["id"]
    app_client["s"].assign(app_client["staff"].id, other)
    assert _archive(c, admin, aid).status_code == 200

    rows = {r["id"]: r for r in c.get("/api/accounts", headers=authz(admin)).json()}
    assert rows[aid]["is_archived"] is True
    assert rows[other]["is_archived"] is False
    staff_rows = c.get("/api/accounts", headers=authz(staff)).json()
    assert other in [r["id"] for r in staff_rows] and aid not in [r["id"] for r in staff_rows]


def test_archive_is_idempotent_and_audits_only_real_changes(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    aid = app_client["a"]["id"]
    s = app_client["s"]
    assert _archive(c, admin, aid).status_code == 200
    assert _archive(c, admin, aid).status_code == 200
    assert len(s.audit_query(action="account_archive", account_id=aid)) == 1
    assert s.audit_query(action="account_archive", account_id=aid)[0]["actor"] == "admin"
    assert _archive(c, admin, aid, "unarchive").status_code == 200
    assert _archive(c, admin, aid, "unarchive").status_code == 200
    assert len(s.audit_query(action="account_unarchive", account_id=aid)) == 1


def test_archived_scope_refused_in_chat_and_external_faq(app_client):
    c = app_client["client"]
    admin, staff = login(c, "admin", "adminpass"), login(c, "staff", "staffpass")
    aid, other = app_client["a"]["id"], app_client["b"]["id"]
    app_client["s"].assign(app_client["staff"].id, other)
    cred = _issue(c, admin, aid)
    other_cred = _issue(c, admin, other)
    assert _archive(c, admin, aid).status_code == 200

    r = c.post("/api/chat", headers=authz(staff),
               json={"account_id": aid, "question": "hello"})
    assert r.status_code == 403 and r.json()["detail"] == "account archived"
    headers = {"X-API-Key": cred["key_id"], "X-API-Secret": cred["secret"]}
    r = c.post("/ext/faq", headers=headers, json={"question": "hello"})
    assert r.status_code == 403 and r.json()["detail"] == "account archived"

    # Active accounts behave exactly as before.
    assert c.post("/api/chat", headers=authz(staff),
                  json={"account_id": other, "question": "hello"}).status_code == 200
    ok = {"X-API-Key": other_cred["key_id"], "X-API-Secret": other_cred["secret"]}
    assert c.post("/ext/faq", headers=ok, json={"question": "hello"}).status_code == 200


def test_cascade_hides_documents_chunks_and_jobs_then_restores(app_client):
    c = app_client["client"]
    admin, staff = login(c, "admin", "adminpass"), login(c, "staff", "staffpass")
    aid, other = app_client["a"]["id"], app_client["b"]["id"]
    s = app_client["s"]
    s.assign(app_client["staff"].id, other)
    doc_a = _upload(c, staff, aid, "a.txt")
    doc_b = _upload(c, staff, other, "b.txt")
    s.add_chunks(doc_a, [Chunk(content="alpha secret", embedding=[1.0, 0.0])])
    s.add_chunks(doc_b, [Chunk(content="beta secret", embedding=[1.0, 0.0])])
    scope = lambda account: Scope(user=staff, account_id=account, caller="internal")
    assert s.get_document(doc_a) is not None
    assert s.document_content(doc_a)["total"] == 1
    assert s.search([1.0, 0.0], scope(aid))
    assert len(s.list_documents(scope(aid))) == 1

    assert _archive(c, admin, aid).status_code == 200
    assert s.get_document(doc_a) is None
    assert s.document_content(doc_a) == {"chunks": [], "total": 0}
    assert s.list_documents(scope(aid)) == []
    assert s.search([1.0, 0.0], scope(aid)) == []
    claimed = s.claim_job()
    assert claimed is not None and claimed["document_id"] == doc_b  # archived job skipped

    assert _archive(c, admin, aid, "unarchive").status_code == 200
    assert s.get_document(doc_a) is not None
    assert s.document_content(doc_a)["total"] == 1
    assert s.search([1.0, 0.0], scope(aid))
    assert s.get_document(doc_b) is not None  # other account unaffected throughout
    assert s.search([1.0, 0.0], scope(other))
