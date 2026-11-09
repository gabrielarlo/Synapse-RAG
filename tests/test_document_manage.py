"""Document replace/version/delete, worker race safety, and category tagging."""
import os
import sys
import threading
import time

import pytest

from app.store import Chunk
from conftest import authz, login

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "worker"))
import worker as ingest  # noqa: E402

UPLOAD_DIR = os.environ["UPLOAD_DIR"]


def _upload(c, tok, aid, body=b"hello world", name="a.txt"):
    return c.post("/api/documents", headers=authz(tok),
                  params={"account_id": aid}, files={"file": (name, body)})


def _replace(c, tok, did, body=b"new body", name="b.txt"):
    return c.put(f"/api/documents/{did}", headers=authz(tok),
                 files={"file": (name, body)})


def test_replace_bumps_version_and_requeues(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]

    r = _replace(c, tok, did)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "queued" and body["version"] == 2

    s = app_client["app"].state.ctx["store"]
    doc = s.get_document(did)
    assert doc["version"] == 2
    assert doc["filename"] == "a.txt"  # file-only PUT keeps the name
    jobs = [j for j in s.jobs.values() if j["document_id"] == did]
    assert len(jobs) == 1 and jobs[0]["account_id"] == aid
    assert not [ch for ch in s.chunks if ch["document_id"] == did]


def test_replace_sets_updated_at(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    s = app_client["app"].state.ctx["store"]
    before = s.get_document(did)["updated_at"]
    assert before  # uploads carry a timestamp from creation

    time.sleep(0.01)
    r = _replace(c, tok, did)
    assert r.status_code == 200, r.text
    after = s.get_document(did)["updated_at"]
    assert after and after >= before
    assert r.json()["updated_at"] == after


def test_replace_supersedes_inflight_worker(app_client):
    s, aid = app_client["s"], app_client["a"]["id"]
    res = s.create_document("a.txt", aid, False, app_client["staff"].id)
    did, job1 = res["document"]["id"], res["job_id"]
    assert s.claim_job()["id"] == job1

    assert s.replace_document(did, None)["version"] == 2
    with pytest.raises(ValueError):
        s.add_chunks(did, [Chunk("stale content", [0.0] * 8)], job_id=job1)
    assert s.finish_job(job1, True) is False
    assert not [ch for ch in s.chunks if ch["document_id"] == did]


def test_delete_supersedes_inflight_worker(app_client):
    s, aid = app_client["s"], app_client["a"]["id"]
    res = s.create_document("a.txt", aid, False, app_client["staff"].id)
    did, job1 = res["document"]["id"], res["job_id"]
    assert s.claim_job()["id"] == job1

    assert s.delete_document(did) == "a.txt"
    with pytest.raises(ValueError):
        s.add_chunks(did, [Chunk("x", [0.0] * 8)], job_id=job1)
    assert s.finish_job(job1, True) is False


def test_delete_removes_document_chunks_and_jobs(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    r = c.delete(f"/api/documents/{did}", headers=authz(tok))
    assert r.status_code == 200 and r.json()["deleted"] is True

    s = app_client["app"].state.ctx["store"]
    assert s.get_document(did) is None
    assert not [j for j in s.jobs.values() if j["document_id"] == did]
    assert not [ch for ch in s.chunks if ch["document_id"] == did]
    assert not os.path.exists(os.path.join(UPLOAD_DIR, did))


def test_oversize_replace_keeps_previous_file_and_state(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid, body=b"original bytes").json()["document_id"]
    app_client["app"].state.ctx["settings"].MAX_UPLOAD_MB = 0

    r = _replace(c, tok, did, body=b"x" * 32)
    assert r.status_code == 413
    assert open(os.path.join(UPLOAD_DIR, did), "rb").read() == b"original bytes"
    doc = app_client["app"].state.ctx["store"].get_document(did)
    assert doc["version"] == 1 and doc["status"] == "queued"


def test_replace_restores_file_when_db_write_fails(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid, body=b"original bytes").json()["document_id"]
    s = app_client["app"].state.ctx["store"]

    def boom(*_a, **_k):
        raise RuntimeError("db down")

    s.replace_document = boom
    r = _replace(c, tok, did, body=b"replacement")
    assert r.status_code == 500
    assert open(os.path.join(UPLOAD_DIR, did), "rb").read() == b"original bytes"
    assert not [p for p in os.listdir(UPLOAD_DIR) if ".bak." in p or ".tmp." in p]


def test_concurrent_replaces_are_serialized(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    s = app_client["app"].state.ctx["store"]

    orig = s.replace_document
    active, peak, guard = 0, 0, threading.Lock()

    def slow(doc_id, filename):
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(0.05)  # widen the race window
            return orig(doc_id, filename)
        finally:
            with guard:
                active -= 1

    s.replace_document = slow
    out = []
    threads = [threading.Thread(target=lambda: out.append(_replace(c, tok, did)))
               for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert peak == 1, "per-document lock did not serialize the replaces"
    assert all(r.status_code == 200 for r in out)
    assert s.get_document(did)["version"] == 3


def test_replace_and_delete_authorization(app_client):
    c = app_client["client"]
    staff = login(c, "staff", "staffpass")
    admin = login(c, "admin", "adminpass")
    # internal doc uploaded by staff: staff may manage it, another user may not
    r = c.post("/api/documents", headers=authz(staff),
               params={"internal": "true"}, files={"file": ("i.txt", b"x")})
    did = r.json()["document_id"]
    assert _replace(c, staff, did).status_code == 200

    # admin can manage it too
    assert _replace(c, admin, did).status_code == 200

    # staff cannot touch an account they are not assigned to
    b = app_client["b"]["id"]
    rb = c.post("/api/documents", headers=authz(admin),
                params={"account_id": b}, files={"file": ("b.txt", b"x")})
    bdid = rb.json()["document_id"]
    assert _replace(c, staff, bdid).status_code == 403
    assert c.delete(f"/api/documents/{bdid}", headers=authz(staff)).status_code == 403

    assert c.delete("/api/documents/not-a-uuid",
                    headers=authz(admin)).status_code == 404
    assert c.delete("/api/documents/00000000-0000-0000-0000-000000000000",
                    headers=authz(admin)).status_code == 404


def test_list_documents_exposes_version_and_category(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    _upload(c, tok, aid)
    rows = c.get("/api/documents", headers=authz(tok),
                 params={"account_id": aid}).json()
    assert rows and rows[0]["version"] == 1 and "category" in rows[0]


def test_worker_tags_category_and_survives_tag_failure(app_client):
    s, aid = app_client["s"], app_client["a"]["id"]
    s.create_document("a.txt", aid, False, app_client["staff"].id)
    doc_id = list(s.documents)[0]
    with open(os.path.join(UPLOAD_DIR, doc_id), "wb") as f:
        f.write(b"contract body")

    class TagFails:
        def embed(self, texts):
            return [[0.0] * 8 for _ in texts]

        def tag_document(self, text):
            raise RuntimeError("decision model down")

    assert ingest.run_once(s, TagFails()) is True
    doc = s.get_document(doc_id)
    assert doc["status"] == "ready" and doc["category"] is None
    assert any(ch["document_id"] == doc_id for ch in s.chunks)


def test_chat_category_follows_retrieved_documents(app_client):
    s, aid = app_client["s"], app_client["a"]["id"]
    c = app_client["client"]
    tok = login(c, "admin", "adminpass")

    def seed(name, text, category):
        d = s.create_document(name, None, True, app_client["admin"].id)["document"]
        s.add_chunks(d["id"], [Chunk(text, [0.0] * 8)])
        d["category"] = category
        return d["id"]

    seed("contract.txt", "the contract text", "contract")
    r = c.post("/api/chat", headers=authz(tok),
               json={"question": "who signed the contract?"})
    assert r.json()["category"] == "contract"

    seed("policy.txt", "the policy text", "policy")
    r = c.post("/api/chat", headers=authz(tok),
               json={"question": "who signed the contract?"})
    assert r.json()["category"] == "general"  # mixed categories -> triage guess


def test_view_document_returns_metadata_and_chunks(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    s = app_client["app"].state.ctx["store"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    s.add_chunks(did, [Chunk("first part", [0.0] * 8),
                       Chunk("second part", [0.0] * 8)])

    r = c.get(f"/api/documents/{did}", headers=authz(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == "a.txt" and body["version"] == 1
    assert body["chunks"] == ["first part", "second part"]
    assert body["chunk_count"] == 2 and body["truncated"] is False
    assert body["uploaded_by"] == "staff"  # username, not the raw id
    assert body["created_at"] and body["updated_at"]


def test_view_document_requires_authentication(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    assert c.get(f"/api/documents/{did}").status_code == 401


def test_view_document_authorization(app_client):
    c = app_client["client"]
    admin = login(c, "admin", "adminpass")
    staff = login(c, "staff", "staffpass")
    b = app_client["b"]["id"]

    rb = c.post("/api/documents", headers=authz(admin),
                params={"account_id": b}, files={"file": ("b.txt", b"x")})
    bdid = rb.json()["document_id"]
    assert c.get(f"/api/documents/{bdid}", headers=authz(staff)).status_code == 403
    assert c.get(f"/api/documents/{bdid}", headers=authz(admin)).status_code == 200

    ri = c.post("/api/documents", headers=authz(admin),
                params={"internal": "true"}, files={"file": ("i.txt", b"x")})
    assert c.get(f"/api/documents/{ri.json()['document_id']}",
                 headers=authz(staff)).status_code == 200

    assert c.get("/api/documents/not-a-uuid", headers=authz(admin)).status_code == 404
    assert c.get("/api/documents/00000000-0000-0000-0000-000000000000",
                 headers=authz(admin)).status_code == 404


def test_view_document_caps_chunk_payload(app_client):
    c, aid = app_client["client"], app_client["a"]["id"]
    s = app_client["app"].state.ctx["store"]
    tok = login(c, "staff", "staffpass")
    did = _upload(c, tok, aid).json()["document_id"]
    s.add_chunks(did, [Chunk(f"chunk {i}", [0.0] * 8) for i in range(60)])

    body = c.get(f"/api/documents/{did}", headers=authz(tok)).json()
    assert len(body["chunks"]) == 50
    assert body["chunk_count"] == 60 and body["truncated"] is True


class _OcrOllama:
    """Minimal worker double: OCR + embed + tag, no network."""

    def __init__(self, text="ocr text from image", fail=None):
        self.text = text
        self.fail = fail

    def extract_image_text(self, data):
        if self.fail:
            raise ValueError(self.fail)
        return self.text

    def embed(self, texts):
        return [[0.0] * 8 for _ in texts]

    def tag_document(self, text):
        return "other"


def _image_job(app_client, name="scan.png", body=b"\x89PNG\r\n\x1a\nfake"):
    s, aid = app_client["s"], app_client["a"]["id"]
    res = s.create_document(name, aid, False, app_client["staff"].id)
    did = res["document"]["id"]
    with open(os.path.join(UPLOAD_DIR, did), "wb") as f:
        f.write(body)
    return s, did


def test_image_upload_is_ocrd(app_client):
    s, did = _image_job(app_client)
    assert ingest.run_once(s, _OcrOllama()) is True
    doc = s.get_document(did)
    assert doc["status"] == "ready" and doc["category"] == "other"
    assert any("ocr text" in ch["content"] for ch in s.chunks)


def test_image_without_text_fails_with_reason(app_client):
    s, did = _image_job(app_client)
    ingest.run_once(s, _OcrOllama(text="   "))
    doc = s.get_document(did)
    assert doc["status"] == "failed"
    assert "no text could be extracted" in doc["error"]


def test_image_without_vision_model_fails_with_reason(app_client):
    s, did = _image_job(app_client)
    ingest.run_once(s, _OcrOllama(fail="vision model not configured"))
    doc = s.get_document(did)
    assert doc["status"] == "failed"
    assert "vision model not configured" in doc["error"]


def test_image_over_ocr_cap_fails_with_reason(app_client):
    s, did = _image_job(app_client, body=b"x" * (ingest.OCR_MAX_BYTES + 1))
    ingest.run_once(s, _OcrOllama())
    doc = s.get_document(did)
    assert doc["status"] == "failed" and "too large for OCR" in doc["error"]


def test_extract_image_text_requires_a_vision_model():
    from app.ollama import Ollama

    o = Ollama("http://x", "g", "e", "d1:2b")
    with pytest.raises(ValueError, match="vision model not configured"):
        o.extract_image_text(b"bytes")
