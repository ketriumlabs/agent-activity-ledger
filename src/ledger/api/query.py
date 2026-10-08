from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BeforeValidator

from ledger.api.deps import get_repository, require_api_key
from ledger.core.events import EventRecord
from ledger.store.repository import EventRepository

router = APIRouter(tags=["query"])


def _strict_query_datetime(value: object) -> object:
    """Reject numeric Unix timestamps; the query contract is ISO date-time."""
    if isinstance(value, str):
        if "T" not in value and "t" not in value:
            raise ValueError("must be an ISO 8601 date-time string")
        return value
    raise ValueError("must be an ISO 8601 date-time string")


QueryDateTime = Annotated[datetime, BeforeValidator(_strict_query_datetime)]


@router.get("/v1/events", dependencies=[Depends(require_api_key)])
def list_events(
    repo: Annotated[EventRepository, Depends(get_repository)],
    agent: str | None = None,
    type: str | None = None,  # noqa: A002 - matches the query param name intentionally
    money: bool = False,
    ts_from: QueryDateTime | None = None,
    ts_to: QueryDateTime | None = None,
    cursor: str | None = None,
    limit: Annotated[int, Query(le=200, ge=1)] = 50,
) -> list[EventRecord]:
    return repo.query(
        agent=agent,
        action_type=type,
        ts_from=ts_from,
        ts_to=ts_to,
        money_only=money,
        cursor=cursor,
        limit=limit,
    )
