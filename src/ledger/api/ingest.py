from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, ValidationError

from ledger.api.deps import get_repository, require_api_key
from ledger.api.errors import validation_problem
from ledger.core.events import EventIn
from ledger.store.repository import EventRepository

router = APIRouter(tags=["ingest"])

MAX_BATCH = 100


class EventOut(BaseModel):
    id: str
    hash: str
    prev_hash: str
    deduped: bool = False


class BatchResult(BaseModel):
    accepted: list[EventOut] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)


def _validate_metadata_size(event: EventIn) -> None:
    from ledger.core.events import MAX_METADATA_BYTES

    if event.metadata_size_bytes() > MAX_METADATA_BYTES:
        raise validation_problem("metadata exceeds 8KB size cap")


@router.post("/v1/events", status_code=201, dependencies=[Depends(require_api_key)])
def ingest_events(
    payload: dict[str, Any] | list[dict[str, Any]],
    repo: Annotated[EventRepository, Depends(get_repository)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> EventOut | BatchResult:
    if isinstance(payload, dict):
        try:
            event = EventIn.model_validate(payload)
        except ValidationError as exc:
            raise validation_problem(str(exc)) from exc
        _validate_metadata_size(event)
        result = repo.insert(event, idempotency_key=idempotency_key)
        return EventOut(
            id=result.record.id,
            hash=result.record.hash,
            prev_hash=result.record.prev_hash,
            deduped=result.deduped,
        )

    if len(payload) > MAX_BATCH:
        raise validation_problem(f"batch exceeds max size of {MAX_BATCH}")

    accepted: list[EventOut] = []
    errors: list[dict[str, str]] = []
    for i, item in enumerate(payload):
        try:
            event = EventIn.model_validate(item)
            _validate_metadata_size(event)
        except Exception as exc:  # noqa: BLE001 - reported per-item, not raised
            errors.append({"index": str(i), "detail": str(exc)})
            continue
        result = repo.insert(event, idempotency_key=idempotency_key)
        accepted.append(
            EventOut(
                id=result.record.id,
                hash=result.record.hash,
                prev_hash=result.record.prev_hash,
                deduped=result.deduped,
            )
        )
    return BatchResult(accepted=accepted, errors=errors)
