from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ledger.store import connect, migrate
from ledger.store.repository import EventRepository


@pytest.fixture
def conn(tmp_path) -> Iterator[sqlite3.Connection]:
    c = connect(tmp_path / "test.db")
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn: sqlite3.Connection) -> EventRepository:
    return EventRepository(conn)
