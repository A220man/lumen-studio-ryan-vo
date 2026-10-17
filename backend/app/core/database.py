"""SQLite persistence layer.

A single shared connection (thread-safe via a lock) keeps the schema
simple for the initial deployment.  The connection is shared across
threads because ``check_same_thread=False`` is set; all writes are
guarded by ``_lock``.
"""

from __future__ import annotations


import sqlite3
import threading
from pathlib import Path

from fastapi import Request

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vtables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    field_name  TEXT    NOT NULL,
    base_address TEXT,
    slots       TEXT    NOT NULL,          -- JSON array of string|null
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS resolutions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vtable_id   INTEGER NOT NULL,
    code        TEXT    NOT NULL,
    matches     TEXT    NOT NULL,          -- JSON array of resolution match objects
    created_at  TEXT    NOT NULL,
    FOREIGN KEY (vtable_id) REFERENCES vtables (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resolutions_vtable ON resolutions(vtable_id);
CREATE INDEX IF NOT EXISTS idx_vtables_name ON vtables(name);
"""


def _url_to_path(database_url: str) -> str:
    """``sqlite:///./lumen.db`` → ``./lumen.db``; ``:memory:`` supported."""
    if database_url == "sqlite:///:memory:":
        return ":memory:"
    if database_url.startswith("sqlite:///"):
        return database_url[len("sqlite:///"):]
    return database_url


class Database:
    """Thin SQLite wrapper with a thread-safe shared connection."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._path = _url_to_path(database_url)
        self._lock = threading.Lock()
        if self._path == ":memory:":
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
        else:
            # Ensure parent directory exists for file-based databases.
            p = Path(self._path)
            if p != Path(":memory:"):
                p.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # -- schema ---------------------------------------------------------

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    # -- queries --------------------------------------------------------

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all matching rows."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE, commit, and return the cursor."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def get_db(request: Request) -> Database:
    """FastAPI dependency: read the Database from app state."""
    return request.app.state.db