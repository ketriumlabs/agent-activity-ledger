"""Tamper-evident hash chain over ledger events.

hash = SHA-256(canonical_json(event minus hash/prev_hash) || prev_hash)

This proves tamper-EVIDENCE (edits are detectable by re-walking the
chain), not tamper-PROOFING — an attacker with database write access
can rewrite the whole chain from a point forward. Exported chain-head
checkpoints (e.g. printed in digest emails) are the mitigation; see
docs/threat-model.md.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from ledger.core.canonical import canonical_json

GENESIS_HASH = "0" * 64


def _hashable_fields(event: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in event.items() if k not in ("hash", "prev_hash")}


def compute_hash(event: dict[str, Any], prev_hash: str) -> str:
    """Compute the chain hash for an event dict, given the previous entry's hash."""
    payload = canonical_json(_hashable_fields(event))
    digest = hashlib.sha256(payload + prev_hash.encode("ascii")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class ChainVerifyResult:
    ok: bool
    length: int
    head_hash: str | None
    first_bad_id: str | None = None
    reason: str | None = None


def verify_chain(events: list[dict[str, Any]]) -> ChainVerifyResult:
    """Re-walk a full ordered list of stored event dicts and verify the chain.

    Each event dict must contain: id, hash, prev_hash, plus all client fields.
    """
    prev_hash = GENESIS_HASH
    for event in events:
        expected = compute_hash(event, prev_hash)
        if event.get("prev_hash") != prev_hash:
            return ChainVerifyResult(
                ok=False,
                length=len(events),
                head_hash=None,
                first_bad_id=event.get("id"),
                reason="prev_hash mismatch",
            )
        if event.get("hash") != expected:
            return ChainVerifyResult(
                ok=False,
                length=len(events),
                head_hash=None,
                first_bad_id=event.get("id"),
                reason="hash mismatch",
            )
        prev_hash = expected
    return ChainVerifyResult(
        ok=True, length=len(events), head_hash=prev_hash if events else GENESIS_HASH
    )
