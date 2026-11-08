"""Ingestion worker: polls PG ingestion_jobs (SKIP LOCKED, no broker),
chunks + embeds via Ollama, stores vectors, marks ready/failed, audit-logs."""
from __future__ import annotations

import os
import sys
import time
import traceback

sys.path.insert(0, _api_dir := os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "..", "api"))
if not os.path.isdir(_api_dir):
    # container layout: worker.py sits beside the app/ package (/srv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ollama import Ollama  # noqa: E402
from app.rag import chunk_text  # noqa: E402
from app.store import Chunk  # noqa: E402

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")


def file_text(document_id: str, filename: str) -> str:
    # v1: plain-text uploads read as-is; PDFs get real text extraction.
    # Raw-decoding a PDF yields FlateDecode garbage retrievers can't match
    # and generators can't answer from.
    # shortcut: non-PDF binary formats still read as text.
    for cand in (os.path.join(UPLOAD_DIR, document_id),
                 os.path.join(UPLOAD_DIR, document_id + "_" + filename)):
        if os.path.exists(cand):
            if filename.lower().endswith(".pdf"):
                try:
                    from pypdf import PdfReader
                    text = "\n".join((p.extract_text() or "")
                                     for p in PdfReader(cand).pages)
                    if text.strip():
                        return text.replace("\x00", "")
                except Exception:  # noqa: BLE001 — fall back to raw decode
                    pass
            with open(cand, "rb") as f:
                # PG text cannot store NUL, so strip it or chunk inserts fail
                return f.read().decode("utf-8", errors="ignore").replace("\x00", "")
    return ""


def run_once(store, ollama) -> bool:
    job = store.claim_job()
    if job is None:
        return False
    try:
        text = file_text(job["document_id"], job.get("filename", ""))
        parts = chunk_text(text)
        chunks = [Chunk(content=c, embedding=e) for c, e in
                  zip(parts, ollama.embed(parts))]
        store.add_chunks(job["document_id"], chunks)
        store.finish_job(job["id"], True)
        store.log(actor="worker", action="ingest",
                  account_id=job["account_id"], detail=job["document_id"])
    except Exception as e:  # noqa: BLE001 — job must never stay claimed
        store.finish_job(job["id"], False, f"{type(e).__name__}: {e}")
        traceback.print_exc()
    return True


def main() -> None:
    from app.config import load_settings
    from app.db import PostgresStore
    settings = load_settings()
    store = None
    for _ in range(30):  # external PG may not be up yet at boot
        try:
            store = PostgresStore(settings.database_dsn, connect_tries=1)
            break
        except Exception as e:  # noqa: BLE001 — boot-time backoff
            print(f"worker: db unavailable ({e}), retrying...", flush=True)
            time.sleep(2)
    if store is None:
        raise SystemExit("worker: could not reach database")
    ollama = Ollama(os.environ["OLLAMA_URL"], os.environ.get("OLLAMA_GEN_MODEL", ""),
                    os.environ.get("OLLAMA_EMBED_MODEL", ""),
                    os.environ.get("OLLAMA_DECISION_MODEL", ""))
    while True:
        try:
            if not run_once(store, ollama):
                time.sleep(2)
        except Exception:  # noqa: BLE001 — never let the poll loop die
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
