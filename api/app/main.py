"""App factory: context (settings, store, sessions, ollama, limiters) lives on
app.state.ctx so tests can inject fakes."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings
from .ollama import Ollama
from .routers import accounts, admin, auth, chat, documents, external, health
from .security import RateLimiter
from .sessions import SessionStore
from .store import InMemoryStore


def create_app(store=None, sessions=None, ollama=None) -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="Synapse-RAG")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
        allow_credentials=False,  # Bearer header needs no cookies; "*" + creds is rejected by browsers
        allow_methods=["*"],
        allow_headers=["*"])

    if store is None:
        from .db import PostgresStore
        store = PostgresStore(settings.database_dsn)
    if sessions is None:
        sessions = SessionStore(settings.SESSION_DB_PATH, settings.SESSION_TTL_MIN * 60)
    if ollama is None:
        ollama = Ollama(settings.OLLAMA_URL, settings.OLLAMA_GEN_MODEL,
                        settings.OLLAMA_EMBED_MODEL, settings.OLLAMA_DECISION_MODEL)

    app.state.ctx = {"settings": settings, "store": store, "sessions": sessions,
                     "ollama": ollama, "login_limiter": RateLimiter(),
                     "faq_limiter": RateLimiter()}
    for r in (health, auth, accounts, documents, chat, admin, external):
        app.include_router(r.router)
    return app


app = None
try:
    app = create_app()
except ImportError:
    raise  # real bug (missing dep, typo) — never swallow
except Exception as e:
    # settings/DB failure at import (e.g. test collection with no .env):
    # uvicorn requires env at serve time.
    import sys
    print(f"api: deferred boot ({type(e).__name__}: {e})", file=sys.stderr)
    app = None
