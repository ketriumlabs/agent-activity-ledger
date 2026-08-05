from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import resources
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ledger.api import health, ingest, query, verify
from ledger.api.errors import (
    ProblemError,
    http_exception_handler,
    problem_error_handler,
    request_validation_error_handler,
)
from ledger.config import Settings, get_settings
from ledger.demo import seed_demo_data
from ledger.digest import start_scheduler
from ledger.store import connect, migrate
from ledger.store.apikeys import create_key, create_key_with_value, has_any_key
from ledger.store.repository import EventRepository

PROBLEM_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "detail": {"type": "string"},
    },
    "required": ["type", "title", "status"],
}


def _custom_openapi(app: FastAPI) -> dict[str, Any]:
    # Every error response (401/404/422/...) is actually emitted as RFC 9457
    # problem+json by our exception handlers, not FastAPI's default
    # `application/json` + `{"detail": [...]}` shape it auto-documents.
    # Rewrite the generated schema so the docs match reality — caught by
    # schemathesis's "Undocumented Content-Type" / "Response violates
    # schema" checks against the live server.
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("schemas", {}).update(
        ingest.EXTRA_COMPONENT_SCHEMAS
    )
    # FastAPI's openapi_extra deep-merges into its auto-generated operation
    # rather than replacing it, so setting requestBody there produces a
    # broken schema with both FastAPI's permissive auto `anyOf` and our
    # precise `oneOf` as sibling keywords (a value must then satisfy both —
    # `{}` slipped through generators because they treated the branches as
    # independent alternatives). Overwrite it wholesale here instead.
    schema["paths"]["/v1/events"]["post"]["requestBody"] = ingest.INGEST_REQUEST_BODY
    # A malformed (not just invalid, actually unparseable) JSON body is
    # rejected by Starlette itself as 400, before our route ever runs — a
    # real, unavoidable response FastAPI doesn't auto-document since it
    # only knows about our own declared responses.
    schema["paths"]["/v1/events"]["post"]["responses"]["400"] = {
        "description": "Malformed request body"
    }
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            for status_code, response in operation.get("responses", {}).items():
                if status_code.isdigit() and int(status_code) >= 400:
                    response["content"] = {
                        "application/problem+json": {"schema": PROBLEM_JSON_SCHEMA}
                    }
    app.openapi_schema = schema
    return schema


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
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]

    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    app.include_router(verify.router)

    from ledger.ui.routes import router as ui_router

    app.include_router(ui_router)

    static_dir = resources.files("ledger.ui").joinpath("static")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
