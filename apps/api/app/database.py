"""SQLAlchemy async engine, session factory, FastAPI dependency, and Supabase client singleton."""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from supabase import Client as SupabaseClient
from supabase import create_client

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# SQLAlchemy — pointed at Supabase Postgres via direct asyncpg connection
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.supabase_db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Supabase client — used for Auth operations (sign_up, sign_in_with_password)
#
# Uses the publishable key (sb_publishable_...) — the new-style replacement for
# the legacy anon key. This is safe for auth operations because the client
# library manages session tokens and we enforce our own server-side authz.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_supabase() -> SupabaseClient:
    """Return a cached Supabase client singleton (publishable key, for auth)."""
    return create_client(settings.supabase_url, settings.supabase_publishable_key)
