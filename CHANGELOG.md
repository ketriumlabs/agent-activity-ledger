# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial scaffold: `agent-event.v0` schema, hash-chain core, SQLite store,
  ingest/query/verify API, timeline UI, demo mode, Claude Code + LangChain
  integrations, MCP self-report server.
- Schemathesis fuzz testing of the live OpenAPI surface, wired into CI.

### Fixed
- `GET /v1/events` with a malformed query param (e.g. `ts_to=null`) returned
  FastAPI's default `{"detail": [...]}` shape instead of RFC 9457
  problem+json; `RequestValidationError` now has its own handler.
- `POST /v1/events` validation failures returned 400, undocumented against
  the auto-generated OpenAPI spec (which only documents 201/422); now 422.
- `/v1/events` POST request body was documented as an unconstrained object,
  letting invalid payloads (e.g. `{}`) look "schema-compliant"; the OpenAPI
  schema now accurately reflects `EventIn` (batch items stay permissive,
  matching their intentional best-effort/per-index-error behavior).
- Error response docs claimed `application/json`; all error responses are
  now documented as `application/problem+json` with an accurate schema.
- `Amount.value` (a `Decimal`) had no bounds, so extreme magnitudes could
  round-trip into scientific notation that violated its own documented
  pattern; bounded to `max_digits=14, decimal_places=4`.
- `EventIn.ts` silently accepted bare numeric Unix timestamps via pydantic's
  default datetime coercion despite being documented as an ISO 8601 string;
  numeric input is now rejected explicitly.
- `Settings` dataclass field defaults called `os.environ.get(...)` at class
  *definition* time, so `ledger serve --port/--host` (which sets the env var
  right before constructing `Settings()`) was silently ignored — switched to
  `default_factory` so each `Settings()` reads the current environment.
