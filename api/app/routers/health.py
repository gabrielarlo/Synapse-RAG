from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health", response_model=dict)
def health(request: Request):
    c = request.app.state.ctx
    db_ok = ollama_ok = False
    try:
        c["store"].list_users()
        db_ok = True
    except Exception:
        pass
    try:
        ollama_ok = c["ollama"].healthy()
    except Exception:
        pass
    status = "ok" if (db_ok and ollama_ok) else "degraded"
    return {"status": status, "db": db_ok, "ollama": ollama_ok}
