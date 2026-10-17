"""FastAPI application factory for Lumen Studio.

Usage (local):
    PYTHONPATH=backend uvicorn app.main:app --reload

Usage (Docker):
    see backend/Dockerfile — CMD uvicorn app.main:app --host 0.0.0.0 --port 8000

The ``create_app`` factory accepts an optional ``test_database_url`` so
the test suite can spin up an isolated database per test session.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.resolver import router as resolver_router
from .core.config import settings
from .core.database import Database


def create_app(test_database_url: str | None = None) -> FastAPI:
    """Build a configured FastAPI application instance."""
    settings.validate_startup()

    db_url = test_database_url or settings.database_url
    db = Database(db_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db = db
        app.state.settings = settings
        yield
        db.close()

    app = FastAPI(
        title="Lumen Studio",
        description="AI/ML reverse-engineering assistant: resolve indirect "
        "vtable calls in decompiled code (Ghidra issue #516).",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/api/v1/docs" if settings.demo_mode else None,
        redoc_url="/api/v1/redoc" if settings.demo_mode else None,
        openapi_url="/api/v1/openapi.json",
    )

    # CORS: permissive in demo mode; locked-down in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.demo_mode else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(resolver_router)

    return app


# Module-level instance for `uvicorn app.main:app`
app = create_app()