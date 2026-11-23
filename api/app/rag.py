"""Chunking + RAG pipeline helpers (triage -> retrieval -> generation)."""
from __future__ import annotations

import re

from .store import Chunk, Scope
from .triage import Triage, parse_triage

# Casual greetings / thanks that should stay natural, not FAQ.
# Bounded to short inputs to avoid misclassifying real questions.
_SMALLTALK_RE = re.compile(
    r"^\s*(hi+|hello+|hey+|hiya|howdy|yo|sup|good\s*(morning|afternoon|evening|day)"
    r"|thanks?(\s+you)?|thank\s+you(\s+so\s+much)?|thx|cheers"
    r"|how\s+are\s+you|what'?s\s+up|how'?s\s+it\s+going|bye|goodbye|see\s+ya"
    r"|hey\s+there|hi\s+there|hello\s+there)(\s*[!.,?]+)?\s*$",
    re.IGNORECASE,
)


def is_smalltalk(question: str) -> bool:
    t = question.strip()
    if not t:
        return False
    if len(t) > 50:
        return False
    if _SMALLTALK_RE.match(t):
        return True
    # "thanks, that's helpful!" — tightened to avoid misclassifying e.g. "thanksgiving traditions…"
    # only treat prefix when it's a standalone thanks token
    low = t.lower()
    if re.match(r"^(thanks\b|thank you\b|thx\b)", low):
        return True
    return False


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


def build_smalltalk_prompt(question: str, history: str = "") -> str:
    hist = f"Conversation so far:\n{history}\n\n" if history else ""
    return (
        f"{hist}The user sent a casual greeting or thanks. "
        "Respond naturally, warmly and briefly as a friendly assistant. "
        "Do not use FAQ format (no Q:/A:), do not mention documents, "
        "and keep it to 1-2 sentences.\n\n"
        f"User: {question}")


def build_prompt(question: str, chunks: list[dict], history: str, *, faq: bool = False) -> str:
    ctx = "\n---\n".join(c["content"] for c in chunks) or "(no matching documents)"
    hist = f"Conversation so far:\n{history}\n\n" if history else ""
    if faq:
        instruction = (
            "Answer in FAQ style using ONLY the documents below. "
            "Format exactly as:\nQ: <concise rephrasing of the user's question>\nA: <concise answer>\n"
            "Use plain 'Q: ' and 'A: ' (no ** around them). "
            "Keep the A: under ~80 words; use '- ' bullets only for lists/steps. "
            "Do not add trailing commentary, disclaimers, or extra sections. "
            "If the documents do not contain the answer, say so briefly in the A:.")
    else:
        instruction = (
            "Answer the question using ONLY the documents below."
            " If they do not contain the answer, say so.")
    return f"{hist}{instruction}\n\nDocuments:\n{ctx}\n\nQuestion: {question}"
