"""Event repository: the only place that writes events, so the hash chain
invariant (each write reads the true current head under one transaction)
can't be violated by a second writer.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ledger.core.chain import GENESIS_HASH, compute_hash
from ledger.core.events import EventIn, EventRecord
from ledger.store.db import transaction


def _uuid7() -> str:
    """A time-ordered UUID. Falls back to a manually-built UUIDv7 since the
    stdlib uuid module doesn't gain uuid7() until 3.14."""
    import os
    import time

    unix_ts_ms = int(time.time() * 1000)
    ts_bytes = unix_ts_ms.to_bytes(6, "big")
    rand = os.urandom(10)
    b = bytearray(ts_bytes + rand)
    b[6] = (b[6] & 0x0F) | 0x70  # version 7
    b[8] = (b[8] & 0x3F) | 0x80  # variant 10
    hex_str = b.hex()
    return f"{hex_str[0:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


class IdempotencyConflict(Exception):
    """Raised when an idempotency key was already used with a different payload."""


@dataclass
class InsertResult:
    record: EventRecord
    deduped: bool = False


def _row_to_event_dict(row: sqlite3.Row) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": row["id"],
        "ts": row["ts"],
        "received_at": row["received_at"],
        "actor": {
            "agent": row["agent"],
            **({"session": row["session"]} if row["session"] else {}),
            **({"model": row["model"]} if row["model"] else {}),
        },
        "action": {"type": row["action_type"], "verb": row["verb"]},
        "source": {
            "integration": row["source_integration"],
            **({"version": row["source_version"]} if row["source_version"] else {}),
        },
        "metadata": json.loads(row["metadata"]),
        "prev_hash": row["prev_hash"],
        "hash": row["hash"],
    }
    if row["target"]:
        d["target"] = row["target"]
    if row["justification"]:
        d["justification"] = row["justification"]
    if row["amount_value"] is not None:
        d["amount"] = {"value": row["amount_value"], "currency": row["amount_currency"]}
    return d


def row_to_record(row: sqlite3.Row) -> EventRecord:
    return EventRecord.model_validate(_row_to_event_dict(row))


def _row_to_hashable_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Reconstruct the exact dict shape that was hashed at insert time.

    Must mirror EventRepository.insert()'s `hashable` construction field-for-field —
    in particular amount.value must be a float (JSON-number shaped), not the
    Decimal-precise string stored in the amount_value column, or the recomputed
    hash will never match and every chain will spuriously fail verification.
    """
    d = _row_to_event_dict(row)
    if row["amount_value"] is not None:
        d["amount"] = {"value": float(row["amount_value"]), "currency": row["amount_currency"]}
    return d


class EventRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def head_hash(self) -> str:
        row = self._conn.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        return row["hash"] if row else GENESIS_HASH

    def insert(self, event: EventIn, idempotency_key: str | None = None) -> InsertResult:
        with transaction(self._conn) as conn:
            if idempotency_key is not None:
                existing = conn.execute(
                    "SELECT * FROM events WHERE source_integration = ? AND idempotency_key = ?",
                    (event.source.integration, idempotency_key),
                ).fetchone()
                if existing is not None:
                    return InsertResult(record=row_to_record(existing), deduped=True)

            prev_hash = self.head_hash()
            event_id = _uuid7()
            received_at = datetime.now(UTC)

            hashable = {
                "id": event_id,
                "ts": event.ts.isoformat(),
                "received_at": received_at.isoformat(),
                "actor": event.actor.model_dump(exclude_none=True),
                "action": event.action.model_dump(),
                "source": event.source.model_dump(exclude_none=True),
                "metadata": event.metadata,
            }
            if event.target is not None:
                hashable["target"] = event.target
            if event.justification is not None:
                hashable["justification"] = event.justification
            if event.amount is not None:
                hashable["amount"] = {
                    "value": float(event.amount.value),
                    "currency": event.amount.currency,
                }

            new_hash = compute_hash(hashable, prev_hash)

            conn.execute(
                """
                INSERT INTO events (
                    id, ts, received_at, agent, session, model,
                    action_type, verb, target, amount_value, amount_currency,
                    justification, source_integration, source_version, metadata,
                    prev_hash, hash, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event.ts.isoformat(),
                    received_at.isoformat(),
                    event.actor.agent,
                    event.actor.session,
                    event.actor.model,
                    event.action.type,
                    event.action.verb,
                    event.target,
                    str(event.amount.value) if event.amount else None,
                    event.amount.currency if event.amount else None,
                    event.justification,
                    event.source.integration,
                    event.source.version,
                    json.dumps(event.metadata),
                    prev_hash,
                    new_hash,
                    idempotency_key,
                ),
            )
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            return InsertResult(record=row_to_record(row))

    def query(
        self,
        *,
        agent: str | None = None,
        action_type: str | None = None,
        ts_from: datetime | None = None,
        ts_to: datetime | None = None,
        money_only: bool = False,
        cursor: str | None = None,
        limit: int = 50,
    ) -> list[EventRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if agent:
            clauses.append("agent = ?")
            params.append(agent)
        if action_type:
            clauses.append("action_type = ?")
            params.append(action_type)
        if ts_from:
            clauses.append("ts >= ?")
            params.append(ts_from.isoformat())
        if ts_to:
            clauses.append("ts <= ?")
            params.append(ts_to.isoformat())
        if money_only:
            clauses.append("amount_value IS NOT NULL")
        if cursor:
            # cursor is a public event id (UUIDv7); resolve to its seq so
            # pagination follows true insertion order, not id's ms-precision order.
            clauses.append("seq < (SELECT seq FROM events WHERE id = ?)")
            params.append(cursor)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM events {where} ORDER BY seq DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [row_to_record(r) for r in rows]

    def all_ordered(self) -> list[dict[str, Any]]:
        """Full chain in true insertion order, for verification. Amounts are floats
        here to match how they were hashed at insert time — see _row_to_hashable_dict."""
        rows = self._conn.execute("SELECT * FROM events ORDER BY seq ASC").fetchall()
        return [_row_to_hashable_dict(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
        return int(row["n"])
