"""Pydantic models for the Ketrium Agent Event v0 schema.

Kept in lockstep with schema/agent-event.v0.json — that file is the
cross-project contract; these models are the Python-side enforcement
of the same shape plus server-assigned fields.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ActionType = Literal[
    "purchase",
    "email.send",
    "message.send",
    "file.write",
    "http.request",
    "auth",
    "schedule",
    "custom",
]

MAX_METADATA_BYTES = 8 * 1024


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str = Field(min_length=1, max_length=200)
    session: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ActionType
    verb: str = Field(min_length=1, max_length=500)


class Amount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Decimal
    currency: str = Field(min_length=3, max_length=3)


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    integration: str = Field(min_length=1, max_length=100)
    version: str | None = Field(default=None, max_length=50)


class EventIn(BaseModel):
    """What a client is allowed to submit. No id/hash/received_at — server-assigned."""

    model_config = ConfigDict(extra="forbid")

    ts: datetime
    actor: Actor
    action: Action
    target: str | None = Field(default=None, max_length=500)
    amount: Amount | None = None
    justification: str | None = Field(default=None, max_length=2000)
    source: Source
    metadata: dict[str, Any] = Field(default_factory=dict)

    def metadata_size_bytes(self) -> int:
        import json

        return len(json.dumps(self.metadata).encode("utf-8"))


class EventRecord(EventIn):
    """A stored event: client fields plus server-assigned chain/id fields."""

    id: str
    received_at: datetime
    prev_hash: str
    hash: str

    def is_money_touching(self) -> bool:
        return self.amount is not None
