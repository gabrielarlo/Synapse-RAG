"""Single .env-driven config loader. Fails fast on missing required secrets."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    JWT_SECRET: str
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    OLLAMA_URL: str

    API_PORT: int = 8000
    OLLAMA_GEN_MODEL: str = "llama3.2:3b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text:latest"
    OLLAMA_DECISION_MODEL: str = "llama3.2:3b"
    OLLAMA_VISION_MODEL: str = "lfm3-vl:2b-q4_K_M"  # image OCR; must be vision-capable
    EMBED_DIM: int = 768
    JWT_EXPIRE_MIN: int = 30
    REFRESH_EXPIRE_DAYS: int = 7
    LOGIN_RATE_LIMIT: int = 10
    LOGIN_RATE_WINDOW_S: int = 60
    FAQ_RATE_LIMIT: int = 60
    FAQ_RATE_WINDOW_S: int = 60
    SESSION_TTL_MIN: int = 30
    SESSION_DB_PATH: str = "/data/sessions.db"
    MAX_UPLOAD_MB: int = 50
    CORS_ALLOW_ORIGINS: str = "*"  # comma-separated; "*" for self-hosted v1

    @property
    def database_dsn(self) -> str:
        # Keyword conninfo: no URL-encoding pitfalls (passwords may hold @/:/).
        return (f"host={self.DATABASE_HOST} port={self.DATABASE_PORT} "
                f"dbname={self.DATABASE_NAME} user={self.DATABASE_USER} "
                f"password={self.DATABASE_PASSWORD}")


def load_settings() -> Settings:
    return Settings()  # raises ValidationError naming the missing key
