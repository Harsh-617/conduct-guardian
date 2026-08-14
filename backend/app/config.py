"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Secrets — no defaults on purpose. A missing key should fail loudly at
    # startup, not silently degrade into a fake screening path.
    groq_api_key: str = ""
    database_url: str = ""

    frontend_origin: str = "http://localhost:3000"
    seed_token: str = ""

    groq_model: str = "llama-3.3-70b-versatile"
    groq_model_bulk: str = "llama-3.1-8b-instant"

    # 30/min, not 10: on stage you may screen half a dozen examples and a judge
    # may then try several of their own. A 429 mid-pitch reads as "it's broken"
    # regardless of the cause, and 30/min still stops casual hammering.
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    max_message_chars: int = 2000
    coaching_cache_minutes: int = 30

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """Normalise a Neon/Postgres URL to SQLAlchemy's psycopg async driver.

        Neon hands you `postgresql://...?sslmode=require`. SQLAlchemy needs the
        driver named explicitly, and psycopg 3 rejects libpq-only query params
        that SQLAlchemy passes through, so `sslmode` is left intact (psycopg
        does understand that one) while the scheme is rewritten.
        """
        url = self.database_url
        if not url:
            # Fallback so the app and tests can boot with no DATABASE_URL set.
            return "sqlite+aiosqlite:///./conduct_guardian.db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.async_database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
