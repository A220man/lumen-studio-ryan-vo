"""Shared pytest fixtures for the Lumen Studio backend test-suite.

Environment variables are set *before* importing app modules so that
the global ``settings`` singleton picks up test values.
"""

from __future__ import annotations

import os

# Configure test environment before any app imports.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from app.core.database import Database  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def app():
    """A FastAPI test app backed by an isolated in-memory SQLite database."""
    test_app = create_app(test_database_url="sqlite:///:memory:")
    yield test_app
    test_app.state.db.close()


@pytest.fixture
def db(app) -> Database:
    """The test database instance (same one the app uses)."""
    return app.state.db


@pytest.fixture
def client(app):
    """HTTP-level test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_slots() -> list[str | None]:
    """A minimal vtable slot list for reuse across tests."""
    return [
        "vtable_getType",
        "vtable_addRef",
        "vtable_release",
        "vtable_queryInterface",
        None,           # slot 4 empty
        "vtable_method5",
        "vtable_method6",
        None,           # slot 7 empty
    ]