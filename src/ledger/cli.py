from __future__ import annotations

import os

import typer
import uvicorn

from ledger.config import get_settings
from ledger.store import connect, migrate
from ledger.store.apikeys import create_key, revoke_all

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
