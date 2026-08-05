from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ledger.api.deps import get_repository, require_api_key
from ledger.core.chain import verify_chain
from ledger.store.repository import EventRepository

router = APIRouter(tags=["verify"])


class VerifyOut(BaseModel):
    ok: bool
    length: int
    head_hash: str | None
    first_bad_id: str | None = None
    reason: str | None = None


@router.get("/v1/verify", dependencies=[Depends(require_api_key)])
def verify(repo: Annotated[EventRepository, Depends(get_repository)]) -> VerifyOut:
    events = repo.all_ordered()
    result = verify_chain(events)
    return VerifyOut(
        ok=result.ok,
        length=result.length,
        head_hash=result.head_hash,
        first_bad_id=result.first_bad_id,
        reason=result.reason,
    )
