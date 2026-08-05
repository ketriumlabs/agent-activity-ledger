from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import resources

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ledger.api import health, ingest, query, verify
from ledger.api.errors import ProblemError, problem_error_handler
from ledger.config import Settings, get_settings
from ledger.demo import seed_demo_data
from ledger.digest import start_scheduler
from ledger.store import connect, migrate
from ledger.store.apikeys import create_key, create_key_with_value, has_any_key
from ledger.store.repository import EventRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        conn = connect(settings.db_path)
        migrate(conn)
        app.state.conn = conn
        app.state.settings = settings

        print("Agent Activity Ledger starting with config:")
        print(json.dumps(settings.redacted(), indent=2))

        if not has_any_key(conn):
            if settings.demo:
                # Fixed key in demo mode: the point of --demo is zero-friction exploration.
                create_key_with_value(conn, "demo", label="demo")
                print("Demo mode: API key is 'demo' (Authorization: Bearer demo)")
            else:
                key = create_key(conn, label="default")
                print("=" * 60)
                print(f"Generated API key (shown once): {key}")
                print("Store it now — it is hashed at rest and cannot be recovered.")
                print("=" * 60)

        if settings.demo:
            inserted = seed_demo_data(EventRepository(conn))
            if inserted:
                print(f"Demo mode: seeded {inserted} events")

        scheduler = start_scheduler(conn, settings)

        yield

        if scheduler is not None:
            scheduler.shutdown(wait=False)
        conn.close()

    app = FastAPI(
        title="Agent Activity Ledger",
        version="0.1.0",
        description="A self-hosted bank statement for everything your AI agents did.",
        lifespan=lifespan,
    )

    app.add_exception_handler(ProblemError, problem_error_handler)

    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(verify.router)

    from ledger.ui.routes import router as ui_router

    app.include_router(ui_router)

    static_dir = resources.files("ledger.ui").joinpath("static")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
