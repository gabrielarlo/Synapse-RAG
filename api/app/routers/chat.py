"""Internal chat: auth -> authz -> audit: check -> triage -> RLS retrieval
-> generation. Session memory bound to (user, account)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from httpx import HTTPError as BackendDown

from ..audit import answer_audit
from ..deps import authed, resolve_scope
from ..rag import build_prompt, retrieve, triage_question
from ..schemas import ChatIn, ChatOut
from ..store import Scope, User

router = APIRouter(prefix="/api/chat", tags=["chat"])
EXPIRY_NOTICE = (" Note: your previous session context expired after 30 minutes"
                 " of inactivity, so this answer starts fresh.")


@router.post("", response_model=ChatOut)
def chat(body: ChatIn, request: Request, user: User = Depends(authed)):
    c = request.app.state.ctx
    if body.account_id is not None:
        scope = resolve_scope(request, body.account_id, user)
    else:
        # omitted account = internal-only scope (never any account's content)
        scope = Scope(user=user, account_id=None, caller="internal",
                      is_admin=False)

    # audit: prefix check runs BEFORE triage, admin-only, never touches vectors
    if body.question.startswith("audit: "):
        if user.role != "admin":
            raise HTTPException(403, "audit questions are admin only")
        try:
            sid, expired, _ = c["sessions"].user_message(
                body.session_id, user.id, scope.account_id or "", body.question)
        except PermissionError:
            raise HTTPException(403, "session belongs to another user or account")
        answered, text = answer_audit(body.question, c["store"], scope.account_id)
        c["sessions"].assistant_message(sid, text, category="audit")
        c["store"].log(actor=user.username, action="audit_question",
                        account_id=scope.account_id, detail=body.question[:200])
        if expired:
            text += EXPIRY_NOTICE
        return ChatOut(answer=text, session_id=sid, session_expired=expired,
                       category="audit")

    try:
        triage = triage_question(c["ollama"], body.question,
                                 log=lambda m: c["store"].log(
                                     actor="system", action="triage_fallback",
                                     account_id=scope.account_id, detail=m))

        sid, expired, history = c["sessions"].user_message(
            body.session_id, user.id, scope.account_id or "", body.question)
        chunks = retrieve(c["ollama"], c["store"], scope, body.question)
        answer = c["ollama"].generate(build_prompt(body.question, chunks, history))
    except PermissionError:
        raise HTTPException(403, "session belongs to another user or account")
    except BackendDown:
        raise HTTPException(503, "model backend unavailable, retry later")

    # category follows the retrieved documents when they agree; otherwise
    # keep the triage guess (empty retrieval included)
    cats = {c.get("category") for c in chunks}
    category = cats.pop() if chunks and all(cats) and len(cats) == 1 \
        else triage.category

    c["store"].log(actor=user.username, action="question",
                    account_id=scope.account_id, detail=body.question[:200])
    prefix = ""
    if triage.escalate:
        c["store"].log(actor=user.username, action="escalation",
                        account_id=scope.account_id,
                        detail=f"category={triage.category} "
                               f"department={triage.department}")
        prefix = (f"[Escalated to {triage.department or 'support'}] ")
    # stored raw (no prefix/notice); prefix + notice are response-only
    c["sessions"].assistant_message(sid, answer, category=category,
                                    escalated=triage.escalate,
                                    department=triage.department)
    if expired:
        answer += EXPIRY_NOTICE
    return ChatOut(answer=prefix + answer, session_id=sid,
                   session_expired=expired, escalated=triage.escalate,
                   department=triage.department, category=category)


@router.get("/sessions/{session_id}/history", response_model=dict)
def session_history(session_id: str, request: Request,
                    user: User = Depends(authed)):
    """Restore a persisted session thread (survives page reloads). Access
    mirrors the chat binding: the owning user, and account membership for
    account-scoped sessions."""
    c = request.app.state.ctx
    row = c["sessions"].get_session(session_id)
    if row is None:
        raise HTTPException(404, "unknown session")
    bound_user, bound_account = row[0], row[1]
    if bound_user != user.id:
        raise HTTPException(403, "session belongs to another user or account")
    if bound_account:
        resolve_scope(request, bound_account, user)
    return {"session_id": session_id,
            "turns": c["sessions"].list_turns(session_id)}
