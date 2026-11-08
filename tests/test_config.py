import pytest

from app.config import load_settings


def test_missing_secret_fails_fast(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    # ensure no .env rescue: run from an empty cwd
    monkeypatch.chdir("/tmp")
    with pytest.raises(Exception) as e:
        load_settings()
    assert "JWT_SECRET" in str(e.value) or "DATABASE_PASSWORD" in str(e.value)


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x")
    monkeypatch.setenv("DATABASE_NAME", "n")
    monkeypatch.setenv("DATABASE_USER", "u")
    monkeypatch.setenv("DATABASE_PASSWORD", "p@ss:w/d")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("OLLAMA_URL", "z")
    monkeypatch.chdir("/tmp")
    s = load_settings()
    assert s.database_dsn == "host=localhost port=5432 dbname=n user=u password=p@ss:w/d"
