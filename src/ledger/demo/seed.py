"""Seeds a realistic fake week of agent activity for `--demo` mode.

This is the growth hack: `docker run ... --demo` should be instantly
explorable with zero setup.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ledger.core.events import Action, Actor, Amount, EventIn, Source
from ledger.store.repository import EventRepository


class _ScriptEntry:
    __slots__ = (
        "hours_ago",
        "agent",
        "action_type",
        "verb",
        "target",
        "justification",
        "amount",
        "integration",
    )

    def __init__(
        self,
        hours_ago: int,
        agent: str,
        action_type: str,
        verb: str,
        target: str,
        justification: str | None,
        amount: tuple[str, str] | None,
        integration: str,
    ) -> None:
        self.hours_ago = hours_ago
        self.agent = agent
        self.action_type = action_type
        self.verb = verb
        self.target = target
        self.justification = justification
        self.amount = amount
        self.integration = integration


_SCRIPT = [
    _ScriptEntry(
        168,
        "claude-code",
        "file.write",
        "Wrote src/api/routes.py",
        "local:repo",
        "User asked to scaffold the API",
        None,
        "claude-code-hook",
    ),
    _ScriptEntry(
        150,
        "travel-bot",
        "http.request",
        "Searched flights BLR to DEL",
        "makemytrip.com",
        "User asked: 'find me a Tuesday flight'",
        None,
        "langchain",
    ),
    _ScriptEntry(
        149,
        "travel-bot",
        "purchase",
        "Booked flight BLR to DEL, seat 14C",
        "makemytrip.com",
        "Cheapest Tuesday option, under user's $200 cap",
        ("129.99", "USD"),
        "langchain",
    ),
    _ScriptEntry(
        120,
        "email-agent",
        "email.send",
        "Sent meeting confirmation to client",
        "client@example.com",
        "User asked to confirm the Thursday meeting",
        None,
        "claude-code-hook",
    ),
    _ScriptEntry(
        96,
        "shopping-bot",
        "purchase",
        "Bought replacement laptop charger",
        "amazon.com",
        "User's charger broke, asked to reorder the same model",
        ("34.50", "USD"),
        "curl",
    ),
    _ScriptEntry(
        72,
        "claude-code",
        "file.write",
        "Refactored auth middleware",
        "local:repo",
        None,
        None,
        "claude-code-hook",
    ),
    _ScriptEntry(
        48,
        "calendar-agent",
        "schedule",
        "Scheduled dentist appointment",
        "calendly.com",
        "User asked to book the next available slot",
        None,
        "mcp",
    ),
    _ScriptEntry(
        30,
        "subscription-bot",
        "purchase",
        "Renewed cloud storage plan",
        "dropbox.com",
        "Auto-renewal per standing user instruction",
        ("9.99", "USD"),
        "curl",
    ),
    _ScriptEntry(
        10,
        "email-agent",
        "email.send",
        "Replied to invoice inquiry",
        "vendor@example.com",
        None,
        None,
        "claude-code-hook",
    ),
    _ScriptEntry(
        2,
        "travel-bot",
        "http.request",
        "Checked flight status BLR-DEL",
        "makemytrip.com",
        None,
        None,
        "langchain",
    ),
]


def seed_demo_data(repo: EventRepository) -> int:
    if repo.count() > 0:
        return 0

    now = datetime.now(UTC)
    inserted = 0
    for entry in _SCRIPT:
        event = EventIn(
            ts=now - timedelta(hours=entry.hours_ago),
            actor=Actor(agent=entry.agent, session="demo-session"),
            action=Action(type=entry.action_type, verb=entry.verb),  # type: ignore[arg-type]
            target=entry.target,
            justification=entry.justification,
            amount=Amount(value=Decimal(entry.amount[0]), currency=entry.amount[1])
            if entry.amount
            else None,
            source=Source(integration=entry.integration, version="0.1.0"),
        )
        repo.insert(event)
        inserted += 1
    return inserted
