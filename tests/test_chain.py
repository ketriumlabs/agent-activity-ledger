from __future__ import annotations

import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from ledger.core.chain import GENESIS_HASH, compute_hash, verify_chain


def _build_chain(n: int) -> list[dict]:
    events = []
    prev = GENESIS_HASH
    for i in range(n):
        event = {"id": f"evt-{i}", "seq": i, "verb": f"did thing {i}"}
        h = compute_hash(event, prev)
        event["prev_hash"] = prev
        event["hash"] = h
        events.append(event)
        prev = h
    return events


def test_empty_chain_verifies() -> None:
    result = verify_chain([])
    assert result.ok
    assert result.head_hash == GENESIS_HASH


def test_valid_chain_verifies() -> None:
    events = _build_chain(20)
    result = verify_chain(events)
    assert result.ok
    assert result.length == 20
    assert result.first_bad_id is None


@given(st.integers(min_value=1, max_value=15), st.data())
@settings(max_examples=25)
def test_any_single_field_mutation_is_detected(n: int, data: st.DataObject) -> None:
    events = _build_chain(n)
    tamper_index = data.draw(st.integers(min_value=0, max_value=n - 1))
    tampered = copy.deepcopy(events)
    tampered[tamper_index]["verb"] = tampered[tamper_index]["verb"] + "-tampered"

    result = verify_chain(tampered)
    assert not result.ok
    assert result.first_bad_id == f"evt-{tamper_index}"


def test_reordered_events_are_detected() -> None:
    events = _build_chain(5)
    reordered = [events[0], events[2], events[1], events[3], events[4]]
    result = verify_chain(reordered)
    assert not result.ok


def test_deleted_middle_event_breaks_chain() -> None:
    events = _build_chain(5)
    del events[2]
    result = verify_chain(events)
    assert not result.ok
    assert result.first_bad_id == "evt-3"
