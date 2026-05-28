"""SQLite-backed translation cache for exact-match lookups."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


class TranslationCache:
    """Simple exact-match translation cache backed by SQLite."""

    def __init__(self, db_path: str | Path = "polydrive_cache.db") -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS translations (
                content_hash TEXT NOT NULL,
                source_lang  TEXT NOT NULL,
                target_lang  TEXT NOT NULL,
                translated   TEXT NOT NULL,
                engine       TEXT NOT NULL,
                PRIMARY KEY (content_hash, source_lang, target_lang)
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def lookup(self, text: str, source_lang: str, target_lang: str) -> str | None:
        """Return cached translation or None on miss."""
        h = self._hash(text)
        row = self._conn.execute(
            "SELECT translated FROM translations WHERE content_hash=? AND source_lang=? AND target_lang=?",
            (h, source_lang, target_lang),
        ).fetchone()
        return row[0] if row else None

    def store(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        translated: str,
        engine: str,
    ) -> None:
        """Store a translation in the cache."""
        h = self._hash(text)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO translations (content_hash, source_lang, target_lang, translated, engine)
            VALUES (?, ?, ?, ?, ?)
            """,
            (h, source_lang, target_lang, translated, engine),
        )
        self._conn.commit()

    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        return {"cached_entries": total}

    def close(self) -> None:
        self._conn.close()
