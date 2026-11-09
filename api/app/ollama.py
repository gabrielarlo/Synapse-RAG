"""Minimal Ollama HTTP client (generation, embeddings, decision)."""
from __future__ import annotations

import json
import base64

import httpx

DOC_CATEGORIES = {
    "policy": "Company policy, procedures, rules, or guidelines",
    "contract": "Contracts, agreements, terms, or legal documents",
    "technical": "Technical documentation, product or engineering material",
    "billing": "Invoices, payments, pricing, or refunds",
    "hr": "People, hiring, leave, or employee information",
    "other": "Anything that does not fit the categories above",
}


class Ollama:
    def __init__(self, base_url: str, gen_model: str, embed_model: str,
                 decision_model: str, timeout_s: float = 60.0,
                 vision_model: str = "") -> None:
        self.base = base_url.rstrip("/")
        self.gen_model = gen_model
        self.embed_model = embed_model
        self.decision_model = decision_model
        self.vision_model = vision_model
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
        # Decision-capability models (e.g. d1) score typed questions via
        # /v1/systemone instead of /api/generate. Returns JSON text so the
        # caller's parse_triage fallback still applies.
        # Server caps text+schema at 64 KiB (bytes); triage needs only the gist.
        state = question.encode("utf-8")[:60000].decode("utf-8", "ignore")
        r = self._http.post(
            f"{self.base}/v1/systemone",
            json={"model": self.decision_model, "state": state,
                  "questions": {
                      "category": {
                          "type": "choice",
                          "instructions": "Which label best fits this question?",
                          "criteria": {
                              "general": "General question or small talk",
                              "billing": "Payments, refunds, invoices",
                              "technical": "Product use, errors, troubleshooting",
                              "account": "Login, access, account settings",
                              "complaint": "Dissatisfaction or formal grievance"}},
                      "escalate": {
                          "type": "noul",
                          "instructions": "Should this be escalated to a human?",
                          "criteria": {
                              "true": ("Complaint, incident, billing dispute,"
                                       " legal or safety issue, or likely"
                                       " unanswerable from the docs"),
                              "false": ("Routine question the knowledge base"
                                        " can answer")}},
                      "department": {
                          "type": "choice",
                          "instructions": "If escalated, which team owns it?",
                          "criteria": {
                              "support": "General customer support",
                              "billing": "Payments and refunds team",
                              "technical": "Engineering or product team"}}}})
        r.raise_for_status()
        # Any 200 with an unexpected shape falls back safely instead of
        # raising (parse_triage then applies its drift default).
        a = r.json().get("answers", {}) or {}
        cat = (a.get("category") or {}).get("choice") or "general"
        esc = (a.get("escalate") or {}).get("noul", 0)
        esc = esc if isinstance(esc, (int, float)) else 0
        dep = (a.get("department") or {}).get("choice")
        return json.dumps({"category": cat, "escalate": esc >= 0.5,
                           "department": dep})

    def tag_document(self, text: str) -> str | None:
        """Classify a document into the fixed taxonomy; None when untaggable."""
        state = text.encode("utf-8")[:4000].decode("utf-8", "ignore")
        if not state.strip():
            return None
        r = self._http.post(
            f"{self.base}/v1/systemone",
            json={"model": self.decision_model, "state": state,
                  "questions": {"category": {
                      "type": "choice",
                      "instructions": "Which category best describes this document?",
                      "criteria": DOC_CATEGORIES}}})
        r.raise_for_status()
        choice = ((r.json().get("answers") or {}).get("category") or {}).get("choice")
        return choice if choice in DOC_CATEGORIES else None

    def extract_image_text(self, data: bytes) -> str:
        """OCR an image with the vision model; empty result means no text."""
        if not self.vision_model:
            raise ValueError("vision model not configured")
        r = self._http.post(
            f"{self.base}/api/generate",
            json={"model": self.vision_model, "stream": False,
                  "prompt": "Transcribe every piece of visible text in this"
                            " image exactly. Output only the text.",
                  "images": [base64.b64encode(data).decode()]},
            timeout=180.0)  # OCR is slow; bounded well above the default
        r.raise_for_status()
        return (r.json().get("response") or "").strip()

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

    def tag_document(self, text: str) -> str | None:
        self.calls.append("tag")
        return "other"

    def extract_image_text(self, data: bytes) -> str:
        self.calls.append("ocr")
        return "ocr text from image"

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append("embed")
        dim = 8
        vecs = []
        for t in texts:
            v = [0.0] * dim
            v[sum(map(ord, t)) % dim] = 1.0
            vecs.append(v)
        return vecs
