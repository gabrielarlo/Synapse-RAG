"""App factory: context (settings, store, sessions, ollama, limiters) lives on
app.state.ctx so tests can inject fakes."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import load_settings
from .ollama import Ollama
from .routers import accounts, admin, auth, chat, documents, external, health
from .security import RateLimiter
from .sessions import SessionStore
from .store import InMemoryStore


def create_app(store=None, sessions=None, ollama=None) -> FastAPI:
    settings = load_settings()
    app = FastAPI(
        title="Synapse-RAG",
        description="Multi-tenant RAG API. Internal routes use JWT Bearer auth; "
                    "external routes (`/ext/*`) use X-API-Key / X-API-Secret headers. "
                    "See `/api/docs` (this Swagger UI) and `GET /openapi.json`.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "external", "description": "Third-party RAG via API key/secret"},
            {"name": "credentials", "description": "API key management (admin only)"},
            {"name": "accounts", "description": "Tenant accounts"},
            {"name": "documents", "description": "Knowledge base documents"},
            {"name": "auth", "description": "Login / JWT"},
            {"name": "audit", "description": "Audit trail (admin only)"},
        ],
    )
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
                        settings.OLLAMA_EMBED_MODEL, settings.OLLAMA_DECISION_MODEL,
                        vision_model=settings.OLLAMA_VISION_MODEL)

    app.state.ctx = {"settings": settings, "store": store, "sessions": sessions,
                     "ollama": ollama, "login_limiter": RateLimiter(),
                     "faq_limiter": RateLimiter()}
    for r in (health, auth, accounts, documents, chat, admin, external):
        app.include_router(r.router)

    # Keep /docs as alias for /api/docs (users expect Swagger at /docs)
    @app.get("/docs", include_in_schema=False)
    def docs_alias():
        return RedirectResponse("/api/docs", status_code=307)

    @app.get("/redoc", include_in_schema=False)
    def redoc_alias():
        return RedirectResponse("/api/redoc", status_code=307)

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
