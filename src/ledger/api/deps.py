from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, Header, Request

from ledger.api.errors import unauthorized
from ledger.store.apikeys import verify_key
from ledger.store.repository import EventRepository


def get_conn(request: Request) -> sqlite3.Connection:
    conn: sqlite3.Connection = request.app.state.conn
    return conn


def get_repository(conn: Annotated[sqlite3.Connection, Depends(get_conn)]) -> EventRepository:
    return EventRepository(conn)


def require_api_key(
    conn: Annotated[sqlite3.Connection, Depends(get_conn)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized()
    presented = authorization.split(" ", 1)[1].strip()
    if not verify_key(conn, presented):
        raise unauthorized()
