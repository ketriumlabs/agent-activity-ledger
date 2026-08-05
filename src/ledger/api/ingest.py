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

# The handler takes a raw dict/list (not `EventIn`) so a batch can partially
# succeed with per-item errors instead of FastAPI rejecting the whole request
# on the first invalid item. That leaves FastAPI's auto-generated OpenAPI
# schema for the body as an unconstrained object/array, which schemathesis
# flags as a contract violation (it generates `{}` or garbage-keyed objects,
# sees they match the documented "any object" schema, then gets a real 422
# from EventIn's actual validation). Declaring the true schema here keeps the
# docs honest and gives fuzzers realistic instances to generate from.
#
# ref_template points nested model refs (Actor, Action, ...) at
# #/components/schemas/* instead of the default #/$defs/* — the latter only
# resolves from within this schema's own document, but this schema gets
# spliced into the paths section of the full OpenAPI document by app.py's
# custom openapi(), where #/$defs/* wouldn't resolve. EXTRA_COMPONENT_SCHEMAS
# is merged into components.schemas there so the refs work; INGEST_REQUEST_BODY
# fully replaces (not openapi_extra-merges with) FastAPI's auto-generated
# requestBody, since openapi_extra deep-merges dicts and would otherwise
# leave FastAPI's permissive auto `anyOf` sitting as a sibling of our
# precise `oneOf` — a value then has to satisfy both.
_EVENT_SCHEMA = EventIn.model_json_schema(ref_template="#/components/schemas/{model}")
EXTRA_COMPONENT_SCHEMAS: dict[str, Any] = _EVENT_SCHEMA.pop("$defs", {})
EXTRA_COMPONENT_SCHEMAS["EventIn"] = _EVENT_SCHEMA

INGEST_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {
                "oneOf": [
                    {"$ref": "#/components/schemas/EventIn"},
                    # Batch items are intentionally best-effort: an item that
                    # fails EventIn validation is reported per-index in the
                    # response's `errors` array rather than rejecting the
                    # whole batch, so array items can't be documented as
                    # strictly EventIn-shaped without contradicting that
                    # 201-with-partial-errors behavior.
                    {
                        "type": "array",
                        "items": {"type": "object", "additionalProperties": True},
                        "maxItems": MAX_BATCH,
                    },
                ]
            }
        }
    },
}


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
