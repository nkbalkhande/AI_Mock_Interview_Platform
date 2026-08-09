"""FastAPI application entrypoint.

Builds the app via a factory, wires middleware, exception handlers and the
versioned API router, and manages startup/shutdown (engine disposal).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.services.resumes.resume_vector_store import ResumeVectorStore

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info("Starting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    try:
        ResumeVectorStore().ensure_collection()
    except Exception:  # noqa: BLE001 - Qdrant being down must not block boot
        logger.exception("Could not ensure Qdrant resume collection on startup")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "healthy", "app": settings.APP_NAME}

    return app


app = create_app()
