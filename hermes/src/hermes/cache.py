"""Local SQLite cache for reprinting last results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

__all__ = ["ResultCache"]


class ResultCache:
    """Store the last JSON payload per command name."""

    def __init__(self, path: Path) -> None:
        """Open or create the cache database.

        Args:
            path: SQLite file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS cache (name TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.commit()
        finally:
            connection.close()

    def put(self, name: str, payload: object) -> None:
        """Replace the cached payload for a command.

        Args:
            name: Command key.
            payload: JSON-serializable object.
        """
        blob = json.dumps(payload)
        connection = sqlite3.connect(self._path)
        try:
            connection.execute(
                "INSERT OR REPLACE INTO cache(name, payload) VALUES (?, ?)",
                (name, blob),
            )
            connection.commit()
        finally:
            connection.close()

    def get(self, name: str) -> object | None:
        """Return the last payload for a command.

        Args:
            name: Command key.

        Returns:
            Parsed JSON or None.
        """
        connection = sqlite3.connect(self._path)
        try:
            row = connection.execute("SELECT payload FROM cache WHERE name = ?", (name,)).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        payload: object = json.loads(str(row[0]))
        return payload
