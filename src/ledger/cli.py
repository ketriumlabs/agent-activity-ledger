from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
import uvicorn

from ledger.config import get_settings
from ledger.store import connect, migrate
from ledger.store.apikeys import create_key, revoke_all

# Windows consoles often default to a legacy codepage (cp1252) that can't
# encode characters like the em dash used in a few of this CLI's messages
# (e.g. "OK — 42 events"). Reconfigure to UTF-8 so output doesn't crash or
# get silently mangled there. Done at import time, not inside main(),
# because the `ledger` console script (see pyproject.toml) is registered
# as `ledger.cli:app` — it calls the Typer app object directly and never
# goes through main(), so this must run on import to actually take effect.
if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    # typeshed types sys.stdout as the narrower `TextIO` protocol, which
    # doesn't declare `reconfigure` — it's really an io.TextIOWrapper.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

app = typer.Typer(help="Agent Activity Ledger — a bank statement for your AI agents.")


@app.command()
def serve(
    demo: bool = typer.Option(
        False, "--demo", help="Seed fake activity, use a fixed 'demo' API key"
    ),
    host: str | None = typer.Option(None, help="Override LEDGER_HOST"),
    port: int | None = typer.Option(None, help="Override LEDGER_PORT"),
) -> None:
    """Start the ledger server."""
    if demo:
        os.environ["DEMO"] = "1"
    if host:
        os.environ["LEDGER_HOST"] = host
    if port:
        os.environ["LEDGER_PORT"] = str(port)

    settings = get_settings()
    uvicorn.run("ledger.api.app:create_app", factory=True, host=settings.host, port=settings.port)


@app.command()
def verify() -> None:
    """Verify the hash chain offline, without starting the server."""
    from ledger.core.chain import verify_chain
    from ledger.store.repository import EventRepository

    settings = get_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    events = EventRepository(conn).all_ordered()
    result = verify_chain(events)
    if result.ok:
        typer.echo(f"OK — {result.length} events, head {result.head_hash}")
    else:
        typer.echo(f"TAMPERED at {result.first_bad_id}: {result.reason}", err=True)
        raise typer.Exit(code=1)


@app.command("rotate-key")
def rotate_key() -> None:
    """Revoke all existing API keys and issue a new one."""
    settings = get_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    revoke_all(conn)
    key = create_key(conn, label="rotated")
    typer.echo(f"New API key (shown once): {key}")


@app.command()
def demo() -> None:
    """Seed demo data into the current database without starting the server."""
    from ledger.demo import seed_demo_data
    from ledger.store.repository import EventRepository

    settings = get_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    inserted = seed_demo_data(EventRepository(conn))
    typer.echo(f"Seeded {inserted} demo events")


@app.command("import-claude-code")
def import_claude_code(
    # ruff's B008 exemption for typer.Option only recognizes primitive
    # scalar annotations (str/int/bool/float), not Path — known limitation,
    # not a real "mutable default" bug: typer evaluates this once at import
    # time either way.
    path: Path | None = typer.Option(  # noqa: B008
        None, help="Transcript root to scan (default: ~/.claude/projects)"
    ),
) -> None:
    """Import tool-use activity from local Claude Code session transcripts.

    Safe to re-run: each imported event's idempotency key is the
    transcript's own tool_use id, so nothing is ever double-counted.
    """
    from ledger.importers.claude_code import DEFAULT_TRANSCRIPTS_DIR, iter_all
    from ledger.store.repository import EventRepository

    root = path or DEFAULT_TRANSCRIPTS_DIR
    if not root.exists():
        typer.echo(f"No transcripts directory at {root}", err=True)
        raise typer.Exit(code=1)

    settings = get_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    repo = EventRepository(conn)

    imported = 0
    deduped = 0
    for item in iter_all(root):
        result = repo.insert(item.event, idempotency_key=item.idempotency_key)
        if result.deduped:
            deduped += 1
        else:
            imported += 1

    typer.echo(f"Imported {imported} new events ({deduped} already in the ledger)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
