"""External FAQ: key/secret auth, stateless, own account only.
`audit: ` input is literal text; `internal` docs are never served here."""
from fastapi import APIRouter, Header, HTTPException, Request
from httpx import HTTPError as BackendDown

from ..deps import check_rate, client_ip
from ..rag import build_prompt, retrieve
from ..schemas import ChatOut, FaqIn
from ..security import check_password
from ..store import Scope

router = APIRouter(prefix="/ext/faq", tags=["external"])


@router.post("", response_model=ChatOut)
def faq(body: FaqIn, request: Request, x_api_key: str = Header(default=""),
        x_api_secret: str = Header(default="")):
    c = request.app.state.ctx
    # IP-bound bucket: rotating bogus keys must not escape the limit.
    check_rate(c["faq_limiter"], f"{client_ip(request)}:{x_api_key}",
               c["settings"].FAQ_RATE_LIMIT, c["settings"].FAQ_RATE_WINDOW_S)
    cred = c["store"].get_credential(x_api_key)
    if cred is None or cred["revoked"] or not check_password(x_api_secret,
                                                             cred["secret_hash"]):
        raise HTTPException(401, "invalid credentials")
    scope = Scope(user=None, account_id=cred["account_id"], caller="external",
                  is_admin=False)
    try:
        chunks = retrieve(c["ollama"], c["store"], scope, body.question)
        answer = c["ollama"].generate(build_prompt(body.question, chunks, ""))
    except BackendDown:
        raise HTTPException(503, "model backend unavailable, retry later")
    c["store"].log(actor=f"ext:{x_api_key[:6]}", action="question",
                    account_id=cred["account_id"], detail=body.question[:200])
    return ChatOut(answer=answer, category="external_faq")
