"""Application configuration loaded from environment variables via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Supabase — direct Postgres URL for SQLAlchemy (asyncpg)
    # Format: postgresql+asyncpg://postgres.[project-ref]:<password>@<host>:5432/postgres
    supabase_db_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Supabase project URL (e.g. https://abcxyz.supabase.co)
    supabase_url: str = "https://your-project.supabase.co"

    # Publishable key — new-style sb_publishable_... (replaces legacy anon key)
    # Safe to expose to the frontend/browser. Used to initialise the Supabase client.
    supabase_publishable_key: str = "sb_publishable_..."

    # Secret key — new-style sb_secret_... (replaces legacy service_role key)
    # NEVER expose publicly. Used for admin/server-side Supabase operations.
    supabase_secret_key: str = "sb_secret_..."

    # JWKS URL for verifying Supabase-issued JWTs server-side.
    # Defaults to <supabase_url>/auth/v1/.well-known/jwks.json.
    # Only override if you use a custom auth domain.
    supabase_jwks_url: str = ""

    @property
    def resolved_jwks_url(self) -> str:
        """Return the effective JWKS URL, auto-derived from supabase_url if not set."""
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    # Redis / ARQ
    redis_url: str = "redis://localhost:6379"

    # AI Provider
    ai_provider: Literal["openai", "mock"] = "mock"
    openai_api_key: str = "sk-..."
    openai_model: str = "gpt-4o-mini"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"

    # App
    app_title: str = "Poiro API"
    app_version: str = "0.1.0"
    debug: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
