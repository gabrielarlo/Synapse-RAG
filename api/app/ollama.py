"""Minimal Ollama HTTP client (generation, embeddings, decision)."""
from __future__ import annotations

import httpx


class Ollama:
    def __init__(self, base_url: str, gen_model: str, embed_model: str,
                 decision_model: str, timeout_s: float = 60.0) -> None:
        self.base = base_url.rstrip("/")
        self.gen_model = gen_model
        self.embed_model = embed_model
        self.decision_model = decision_model
        self._http = httpx.Client(timeout=timeout_s)

    def healthy(self) -> bool:
        try:
            return self._http.get(f"{self.base}/api/tags").status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, prompt: str, system: str = "") -> str:
        r = self._http.post(f"{self.base}/api/generate",
                            json={"model": self.gen_model, "prompt": prompt,
                                  "system": system, "stream": False})
        r.raise_for_status()
        return r.json().get("response", "")

    def decide(self, question: str) -> str:
        # No "format": "json" — some runners reject it; the system prompt
        # already constrains output and the caller falls back safely.
        r = self._http.post(
            f"{self.base}/api/generate",
            json={"model": self.decision_model, "stream": False,
                  "system": DECIDE_SYSTEM,
                  "prompt": f"Question: {question}"})
        r.raise_for_status()
        return r.json().get("response", "")

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            r = self._http.post(f"{self.base}/api/embed",
                                json={"model": self.embed_model, "input": t})
            r.raise_for_status()
            j = r.json()
            emb = j.get("embeddings", [[]])[0]
            out.append([float(x) for x in emb])
        return out


DECIDE_SYSTEM = (
    'Classify the user question for a support RAG system. Reply with JSON only:'
    ' {"category": "<short label>", "escalate": <true|false>,'
    ' "department": "<team or null>"}.'
    ' Set escalate=true for complaints, incidents, billing disputes, legal or'
    ' safety issues, or anything the knowledge base likely cannot answer.'
)


class FakeOllama:
    """Deterministic test double. Records calls for order assertions."""

    def __init__(self, triage: dict | None = None) -> None:
        self.calls: list[str] = []
        self.triage = triage or {"category": "general", "escalate": False,
                                 "department": None}

    def healthy(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> str:
        self.calls.append("generate")
        return " grounded answer from context"

    def decide(self, question: str) -> str:
        import json
        self.calls.append("decide")
        return json.dumps(self.triage)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append("embed")
        dim = 8
        vecs = []
        for t in texts:
            v = [0.0] * dim
            v[sum(map(ord, t)) % dim] = 1.0
            vecs.append(v)
        return vecs
