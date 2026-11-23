"""Internal chat: auth -> authz -> audit: check -> triage -> RLS retrieval
-> generation. Session memory bound to (user, account)."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from httpx import HTTPError as BackendDown

from ..a2ui import build_audit_surface, build_chat_surface, extract_a2ui_from_text, merge_surfaces
from ..audit import answer_audit, get_audit_events_for_surface
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
        # A2UI only for answered audit queries; refusals stay text-only
        if answered:
            scope_label = " today (Asia/Manila, platform-wide)" if scope.account_id is None else " today (Asia/Manila, account scoped)"
            events = get_audit_events_for_surface(body.question, c["store"], scope.account_id)
            a2ui = build_audit_surface(session_id=sid, question=body.question, answer=text, events=events, scope_label=scope_label)
        else:
            a2ui = None
        # persist even refusals so history reflects the refusal (audit turns count in list_sessions)
        c["sessions"].assistant_message(sid, text, category="audit", a2ui=a2ui)
        c["store"].log(actor=user.username, action="audit_question",
                        account_id=scope.account_id, detail=body.question[:200])
        if expired:
            text += EXPIRY_NOTICE
        return ChatOut(answer=text, session_id=sid, session_expired=expired,
                       category="audit", a2ui=a2ui)

    try:
        # bind session first so PermissionError is raised before any triage side-effects
        sid, expired, history = c["sessions"].user_message(
            body.session_id, user.id, scope.account_id or "", body.question)
        triage = triage_question(c["ollama"], body.question,
                                 log=lambda m: c["store"].log(
                                     actor="system", action="triage_fallback",
                                     account_id=scope.account_id, detail=m))
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
    # A2UI: deterministic surface from retrieval + triage, plus any
    # agent-emitted ```a2ui fence the generator included.
    answer_clean, llm_surface = extract_a2ui_from_text(answer)
    # store the raw clean answer; prefix/notice are response-only
    deterministic = build_chat_surface(
        session_id=sid, answer=answer_clean, chunks=chunks,
        category=category, escalated=triage.escalate,
        department=triage.department)
    a2ui = merge_surfaces(deterministic, llm_surface)
    c["sessions"].assistant_message(sid, answer_clean, category=category,
                                    escalated=triage.escalate,
                                    department=triage.department,
                                    a2ui=a2ui)
    display = prefix + answer_clean
    if expired:
        display += EXPIRY_NOTICE
    return ChatOut(answer=display, session_id=sid,
                   session_expired=expired, escalated=triage.escalate,
                   department=triage.department, category=category, a2ui=a2ui)


@router.get("/sessions")
def list_sessions(request: Request,
                  user: User = Depends(authed),
                  limit: int = Query(20, ge=1, le=50)):
    """List caller's own sessions (owner-only, limited). Account sessions
    the user no longer belongs to are skipped silently (no abort, no leak)."""
    c = request.app.state.ctx
    rows = c["sessions"].list_sessions(user.id, limit=limit)
    out = []
    for r in rows:
        if r["account_id"]:
            try:
                resolve_scope(request, r["account_id"], user)
            except HTTPException as e:
                if e.status_code == 403:
                    continue  # revoked membership: hide row, keep listing
                raise  # allow 422/other to propagate
        out.append(r)
    return out


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


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, request: Request,
                   user: User = Depends(authed)):
    """Permanently delete a session owned by the caller. Access mirrors the
    history endpoint: owner-only, plus account membership when account-scoped."""
    c = request.app.state.ctx
    row = c["sessions"].get_session(session_id)
    if row is None:
        raise HTTPException(404, "unknown session")
    bound_user, bound_account, _ = row
    if bound_user != user.id:
        raise HTTPException(403, "session belongs to another user or account")
    if bound_account:
        resolve_scope(request, bound_account, user)
    c["sessions"].delete_session(session_id)
    c["store"].log(actor=user.username, action="delete",
                   account_id=bound_account or None,
                   detail=f"session {session_id}")
    return {"deleted": session_id}
