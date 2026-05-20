"""FastAPI application factory with lifespan management and CORS."""

import logging
import logging.config
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base

logger = logging.getLogger(__name__)


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: create DB tables on startup, dispose engine on shutdown."""
    settings = get_settings()
    _configure_logging(settings.log_level)
    logger.info("Starting %s v%s", settings.app_title, settings.app_version)

    # Import all models so SQLAlchemy knows about them before create_all
    import app.auth.models  # noqa: F401
    import app.rooms.models  # noqa: F401
    import app.rounds.models  # noqa: F401
    import app.submissions.models  # noqa: F401
    import app.scores.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables verified/created.")
    yield

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
