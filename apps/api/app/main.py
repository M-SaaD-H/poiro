"""FastAPI application factory with lifespan management and CORS."""

import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import arq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, get_supabase

logger = logging.getLogger(__name__)


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialise shared resources on startup, clean up on shutdown.

    Resources managed here:
      - app.state.redis   — shared ARQ Redis pool; used by routers to enqueue jobs
                            without creating a new connection per request.
      - pubsub_task       — background coroutine that subscribes to Redis Pub/Sub and
                            fans out worker-emitted events to live WebSocket connections.

    Schema management is handled by Supabase SQL migrations (supabase/migrations/).
    """
    settings = get_settings()
    _configure_logging(settings.log_level)
    logger.info("Starting %s v%s", settings.app_title, settings.app_version)

    # Warm up the Supabase client singleton so the first request isn't slower.
    get_supabase()
    logger.info("Supabase client initialised.")

    # Shared ARQ Redis pool — routers read from app.state.redis instead of
    # opening a new pool on every request.
    # If Redis is unavailable at startup the API still starts; job enqueuing
    # and realtime worker broadcasts degrade gracefully until Redis recovers.
    app.state.redis = None
    pubsub_task = None
    try:
        redis_settings = arq.connections.RedisSettings.from_dsn(settings.redis_url)
        app.state.redis = await arq.create_pool(redis_settings)
        logger.info("ARQ Redis pool initialised.")

        # Background Pub/Sub listener — receives events published by the ARQ
        # worker (separate process) and fans them out to in-process WebSocket
        # connections.
        from app.ws.pubsub import pubsub_listener
        pubsub_task = asyncio.create_task(
            pubsub_listener(settings.redis_url),
            name="pubsub_listener",
        )
        logger.info("Pub/Sub listener task started.")
    except Exception as exc:
        logger.warning(
            "Redis unavailable at startup (%s). Job queueing and realtime worker "
            "broadcasts are disabled until Redis is reachable. "
            "Start Redis and restart the server to restore full functionality.",
            exc,
        )

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    if pubsub_task is not None:
        pubsub_task.cancel()
        try:
            await pubsub_task
        except asyncio.CancelledError:
            pass
        logger.info("Pub/Sub listener stopped.")

    if app.state.redis is not None:
        await app.state.redis.aclose()
        logger.info("ARQ Redis pool closed.")

    await engine.dispose()
    logger.info("Database engine disposed. Shutdown complete.")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.auth.router import router as auth_router
    from app.rooms.router import router as rooms_router
    from app.rounds.router import router as rounds_router
    from app.submissions.router import router as submissions_router
    from app.scores.router import router as scores_router
    from app.ws.router import router as ws_router

    app.include_router(auth_router, prefix="/api")
    app.include_router(rooms_router, prefix="/api")
    app.include_router(rounds_router, prefix="/api")
    app.include_router(submissions_router, prefix="/api")
    app.include_router(scores_router, prefix="/api")
    app.include_router(ws_router)  # WS routes don't use /api prefix

    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()
