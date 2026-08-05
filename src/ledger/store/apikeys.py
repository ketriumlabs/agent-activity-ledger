"""API key issuance and verification. Keys are shown once, stored argon2-hashed."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def generate_key() -> str:
    return f"lgr_{secrets.token_urlsafe(32)}"


def create_key(conn: sqlite3.Connection, label: str = "default") -> str:
    return create_key_with_value(conn, generate_key(), label=label)


def create_key_with_value(conn: sqlite3.Connection, key: str, label: str = "default") -> str:
    """Register a caller-supplied key value. Used by demo mode for a fixed 'demo' key."""
    conn.execute(
        "INSERT INTO api_keys (id, key_hash, label, created_at) VALUES (?, ?, ?, ?)",
        (str(uuid4()), _hasher.hash(key), label, datetime.now(UTC).isoformat()),
    )
    conn.commit()
    return key


def verify_key(conn: sqlite3.Connection, presented_key: str) -> bool:
    rows = conn.execute("SELECT key_hash FROM api_keys WHERE revoked_at IS NULL").fetchall()
    for row in rows:
        try:
            if _hasher.verify(row["key_hash"], presented_key):
                return True
        except VerifyMismatchError:
            continue
    return False


def has_any_key(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM api_keys WHERE revoked_at IS NULL").fetchone()
    return int(row["n"]) > 0


def revoke_all(conn: sqlite3.Connection) -> None:
    conn.execute(
        "UPDATE api_keys SET revoked_at = ? WHERE revoked_at IS NULL",
        (datetime.now(UTC).isoformat(),),
    )
    conn.commit()
