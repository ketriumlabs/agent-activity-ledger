from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ledger.core.chain import verify_chain
from ledger.core.events import Action, Actor, Amount, EventIn, Source
from ledger.store.repository import EventRepository


def _event(agent: str = "test-agent", amount: str | None = None) -> EventIn:
    return EventIn(
        ts=datetime.now(UTC),
        actor=Actor(agent=agent),
        action=Action(type="custom", verb="did a thing"),
        amount=Amount(value=Decimal(amount), currency="USD") if amount else None,
        source=Source(integration="test"),
    )


def test_insert_and_verify_chain(repo: EventRepository) -> None:
    for i in range(5):
        repo.insert(_event(agent=f"agent-{i}"))
    result = verify_chain(repo.all_ordered())
    assert result.ok
    assert result.length == 5


def test_rapid_inserts_within_same_millisecond_preserve_chain_order(repo: EventRepository) -> None:
    """Regression test: UUIDv7 ids only sort correctly at ms granularity. A batch
    of inserts that land in the same millisecond must still verify — ordering
    must come from the seq column, not from ORDER BY id."""
    for i in range(50):
        repo.insert(_event(agent=f"agent-{i}"))
    result = verify_chain(repo.all_ordered())
    assert result.ok, result.reason
    assert result.length == 50


def test_money_touching_amount_survives_the_chain(repo: EventRepository) -> None:
    repo.insert(_event(amount="129.99"))
    result = verify_chain(repo.all_ordered())
    assert result.ok, result.reason


def test_idempotency_key_dedupes(repo: EventRepository) -> None:
    event = _event()
    first = repo.insert(event, idempotency_key="key-1")
    second = repo.insert(event, idempotency_key="key-1")
    assert not first.deduped
    assert second.deduped
    assert first.record.id == second.record.id
    assert repo.count() == 1


def test_different_idempotency_keys_both_insert(repo: EventRepository) -> None:
    event = _event()
    repo.insert(event, idempotency_key="key-a")
    repo.insert(event, idempotency_key="key-b")
    assert repo.count() == 2


def test_query_filters_by_agent(repo: EventRepository) -> None:
    repo.insert(_event(agent="alice"))
    repo.insert(_event(agent="bob"))
    results = repo.query(agent="alice")
    assert len(results) == 1
    assert results[0].actor.agent == "alice"


def test_query_money_only_filter(repo: EventRepository) -> None:
    repo.insert(_event(agent="alice"))
    repo.insert(_event(agent="bob", amount="10.00"))
    results = repo.query(money_only=True)
    assert len(results) == 1
    assert results[0].actor.agent == "bob"


def test_pagination_cursor_resolves_id_to_true_insertion_order(repo: EventRepository) -> None:
    ids = [repo.insert(_event(agent=f"agent-{i}")).record.id for i in range(10)]
    page1 = repo.query(limit=4)
    assert [e.id for e in page1] == list(reversed(ids))[:4]
    page2 = repo.query(limit=4, cursor=page1[-1].id)
    assert [e.id for e in page2] == list(reversed(ids))[4:8]
