"""Chunking + RAG pipeline helpers (triage -> retrieval -> generation)."""
from __future__ import annotations

from .store import Chunk, Scope
from .triage import Triage, parse_triage


def chunk_text(text: str, size: int = 250, overlap: int = 50) -> list[str]:
    # Small chunks: a 3B generator loses needles in 1000-word walls, and
    # oversized chunks dilute embedding similarity. ~250 words keeps top-k
    # focused and the prompt short.
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        i += max(size - overlap, 1)
    return [c for c in chunks if c.strip()]


def triage_question(ollama, question: str, log) -> Triage:
    raw = ollama.decide(question)
    t = parse_triage(raw)
    if t.category == "general" and not t.escalate and raw.strip()[:1] != "{":
        log("decision model output unparseable; used safe fallback")
    return t


def retrieve(ollama, store, scope: Scope, question: str, limit: int = 5) -> list[dict]:
    vec = ollama.embed([question])[0]
    return store.search(vec, scope, limit=limit)


def build_prompt(question: str, chunks: list[dict], history: str) -> str:
    ctx = "\n---\n".join(c["content"] for c in chunks) or "(no matching documents)"
    hist = f"Conversation so far:\n{history}\n\n" if history else ""
    return (f"{hist}Answer the question using ONLY the documents below."
            f" If they do not contain the answer, say so.\n\nDocuments:\n{ctx}\n\n"
            f"Question: {question}")
