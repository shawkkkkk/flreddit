from __future__ import annotations

import json
import sqlite3
import zlib
from datetime import datetime, timezone
from pathlib import Path

from .forum import Forum


class StateStoreError(RuntimeError):
    """Raised when a persisted colony snapshot cannot be decoded."""


class SQLiteStore:
    """Transactional restart storage for one authoritative colony state."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS colony_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    schema_version INTEGER NOT NULL,
                    saved_at TEXT NOT NULL,
                    payload BLOB NOT NULL
                )
                """
            )

    def save(self, forum: Forum) -> str:
        saved_at = datetime.now(timezone.utc).isoformat()
        raw = json.dumps(forum.snapshot(), separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload = zlib.compress(raw, level=6)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO colony_state (id, schema_version, saved_at, payload)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    schema_version=excluded.schema_version,
                    saved_at=excluded.saved_at,
                    payload=excluded.payload
                """,
                (self.SCHEMA_VERSION, saved_at, payload),
            )
        return saved_at

    def load(self) -> Forum | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT schema_version, payload FROM colony_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        schema_version, payload = row
        if int(schema_version) != self.SCHEMA_VERSION:
            raise StateStoreError(f"Unsupported Flreddit database schema: {schema_version}")
        try:
            raw = json.loads(zlib.decompress(payload).decode("utf-8"))
            return Forum.from_snapshot(raw)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, zlib.error) as exc:
            raise StateStoreError("The saved Flreddit colony state is invalid.") from exc

    def status(self) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT saved_at, length(payload) FROM colony_state WHERE id = 1"
            ).fetchone()
        return {
            "path": str(self.path),
            "has_snapshot": row is not None,
            "saved_at": row[0] if row else None,
            "compressed_bytes": int(row[1]) if row else 0,
        }
