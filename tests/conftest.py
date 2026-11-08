import os
import sys
import tempfile

os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod-use-12345")
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "1")
os.environ.setdefault("DATABASE_NAME", "db")
os.environ.setdefault("DATABASE_USER", "u")
os.environ.setdefault("DATABASE_PASSWORD", "p")
os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp(prefix="synapse-uploads-"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.ollama import FakeOllama  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.sessions import SessionStore  # noqa: E402
from app.store import InMemoryStore  # noqa: E402


@pytest.fixture()
def store():
    s = InMemoryStore()
    admin = s.create_user("admin", hash_password("adminpass"), "admin")
    staff = s.create_user("staff", hash_password("staffpass"), "staff")
    a = s.create_account("Acme")
    b = s.create_account("Globex")
    s.assign(staff.id, a["id"])
    return {"s": s, "admin": admin, "staff": staff, "a": a, "b": b}


@pytest.fixture()
def app_client(store):
    app = create_app(store=store["s"], sessions=SessionStore(":memory:"),
                     ollama=FakeOllama())
    with TestClient(app) as client:
        yield {"client": client, "app": app, **store}


def login(client, username, password):
    r = client.post("/api/auth/login", json={"username": username,
                                             "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def authz(token):
    return {"Authorization": f"Bearer {token['access_token']}"}
