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

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
OCR_MAX_BYTES = 2 * 1024 * 1024  # base64 bloat + model limits; keep OCR bounded


def file_text(document_id: str, filename: str, ollama=None) -> str:
    # Plain text reads as-is; PDFs and images get real text extraction.
    # Raw-decoding a PDF or PNG yields binary garbage retrievers can't match
    # and generators can't answer from.
    # shortcut: other binary formats (docx, xlsx) still read as text.
    lower = filename.lower()
    base = os.path.basename(filename)  # stored names are untrusted input
    for cand in (os.path.join(UPLOAD_DIR, document_id),
                 os.path.join(UPLOAD_DIR, document_id + "_" + base)):
        if not os.path.exists(cand):
            continue
        if lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                text = "\n".join((p.extract_text() or "")
                                 for p in PdfReader(cand).pages)
                if text.strip():
                    return text.replace("\x00", "")
            except Exception:  # noqa: BLE001 — fall back to raw decode
                pass
        elif lower.endswith(IMAGE_EXTS):
            with open(cand, "rb") as f:
                raw = f.read()
            if len(raw) > OCR_MAX_BYTES:
                raise ValueError(f"image too large for OCR"
                                 f" (max {OCR_MAX_BYTES // (1024 * 1024)} MB)")
            if ollama is None:
                raise ValueError("vision model not configured")
            text = ollama.extract_image_text(raw)
            if not text.strip():
                raise ValueError("no text could be extracted from the image")
            return text.replace("\x00", "")
        with open(cand, "rb") as f:
            # PG text cannot store NUL, so strip it or chunk inserts fail
            return f.read().decode("utf-8", errors="ignore").replace("\x00", "")
    return ""


def run_once(store, ollama) -> bool:
    job = store.claim_job()
    if job is None:
        return False
    try:
        text = file_text(job["document_id"], job.get("filename", ""), ollama)
        parts = chunk_text(text)
        chunks = [Chunk(content=c, embedding=e) for c, e in
                  zip(parts, ollama.embed(parts))]
        store.add_chunks(job["document_id"], chunks, job_id=job["id"])
        category = None
        try:
            category = ollama.tag_document(text)
        except Exception:  # noqa: BLE001 — a tag must never fail ingestion
            category = None
        if store.finish_job(job["id"], True, None, category, job["document_id"]):
            store.log(actor="worker", action="ingest",
                      account_id=job["account_id"], detail=job["document_id"])
    except Exception as e:  # noqa: BLE001 — job must never stay claimed
        # superseded jobs (replaced/deleted mid-ingest) finish as a no-op
        store.finish_job(job["id"], False, f"{type(e).__name__}: {e}",
                         None, job["document_id"])
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
                    os.environ.get("OLLAMA_DECISION_MODEL", ""),
                    vision_model=os.environ.get("OLLAMA_VISION_MODEL")
                    or settings.OLLAMA_VISION_MODEL)
    while True:
        try:
            if not run_once(store, ollama):
                time.sleep(2)
        except Exception:  # noqa: BLE001 — never let the poll loop die
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
