"""External FAQ: key/secret auth, stateless, own account only.
`audit: ` input is literal text; `internal` docs are never served here."""
from fastapi import APIRouter, Header, HTTPException, Request
from httpx import HTTPError as BackendDown

from ..a2ui import build_chat_surface, extract_a2ui_from_text, merge_surfaces
from ..deps import check_rate, client_ip
from ..rag import build_prompt, build_smalltalk_prompt, is_smalltalk, retrieve
from ..schemas import FaqOut, FaqIn
from ..security import check_password
from ..store import Scope

router = APIRouter(prefix="/ext/faq", tags=["external"])


@router.post("", response_model=FaqOut,
             summary="External RAG query",
             description="Stateless RAG for third-party integrators. "
                         "Authenticate with X-API-Key and X-API-Secret headers. "
                         "Answers only from the credential-bound account's own documents.")
def faq(body: FaqIn, request: Request,
        x_api_key: str = Header(default="", description="API key (key_id, e.g. sk_...)"),
        x_api_secret: str = Header(default="", description="API secret (plaintext)")):
    c = request.app.state.ctx
    # IP-bound bucket: rotating bogus keys must not escape the limit.
    check_rate(c["faq_limiter"], f"{client_ip(request)}:{x_api_key}",
               c["settings"].FAQ_RATE_LIMIT, c["settings"].FAQ_RATE_WINDOW_S)
    cred = c["store"].get_credential(x_api_key)
    if cred is None or cred["revoked"] or not check_password(x_api_secret,
                                                             cred["secret_hash"]):
        raise HTTPException(401, "invalid credentials")
    # expiry check (90-day default) — treat expired like revoked
    exp = cred.get("expires_at")
    if exp:
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(exp)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt <= datetime.now(timezone.utc):
                raise HTTPException(401, "key expired")
        except HTTPException:
            raise
        except Exception:
            # unparseable expiry → deny rather than silently allowing
            raise HTTPException(401, "key expired")
    # External scope is built directly from the credential, so it needs the
    # same archived-tenant refusal that resolve_scope gives internal callers.
    if c["store"].is_archived(cred["account_id"]):
        raise HTTPException(403, "account archived")
    scope = Scope(user=None, account_id=cred["account_id"], caller="external",
                  is_admin=False)
    try:
        if is_smalltalk(body.question):
            answer_raw = c["ollama"].generate(build_smalltalk_prompt(body.question, ""))
            answer, llm_surface = extract_a2ui_from_text(answer_raw)
            a2ui = merge_surfaces(None, llm_surface)
            c["store"].log(actor=f"ext:{x_api_key[:6]}", action="question",
                             account_id=cred["account_id"], detail=body.question[:200])
            return FaqOut(answer=answer, category="external_faq", a2ui=a2ui)
        else:
            chunks = retrieve(c["ollama"], c["store"], scope, body.question)
            answer_raw = c["ollama"].generate(build_prompt(body.question, chunks, "", faq=True))
            answer, llm_surface = extract_a2ui_from_text(answer_raw)
            deterministic = build_chat_surface(
                session_id=None, answer=answer, chunks=chunks,
                category="external_faq", escalated=False, department=None)
            a2ui = merge_surfaces(deterministic, llm_surface)
    except BackendDown:
        raise HTTPException(503, "model backend unavailable, retry later")
    c["store"].log(actor=f"ext:{x_api_key[:6]}", action="question",
                     account_id=cred["account_id"], detail=body.question[:200])
    return FaqOut(answer=answer, category="external_faq", a2ui=a2ui)
