"""SQLite connection management: WAL mode, migrations applied at boot."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path


def _migration_files() -> list[tuple[str, str]]:
    """Return (version, sql) pairs sorted by filename, e.g. ('0001_init', '...')."""
    migrations_dir = resources.files("ledger.store").joinpath("migrations")
    out: list[tuple[str, str]] = []
    for entry in sorted(migrations_dir.iterdir(), key=lambda p: p.name):
        if entry.name.endswith(".sql"):
            version = entry.name.removesuffix(".sql")
            out.append((version, entry.read_text(encoding="utf-8")))
    return out


def connect(db_path: str | Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply any migrations not yet recorded in schema_migrations. Returns applied versions."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied_rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    already_applied = {row["version"] for row in applied_rows}

    newly_applied: list[str] = []
    for version, sql in _migration_files():
        if version in already_applied:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(UTC).isoformat()),
            )
        newly_applied.append(version)
    return newly_applied


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Explicit transaction context — sqlite3's autocommit-by-default is easy to misuse."""
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
