# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0](https://github.com/ketriumlabs/agent-activity-ledger/compare/agent-activity-ledger-v0.1.0...agent-activity-ledger-v0.2.0) (2026-08-05)


### Features

* add ledger import-claude-code — pull activity from local transcripts ([26c2504](https://github.com/ketriumlabs/agent-activity-ledger/commit/26c2504687244dac69e1c82e7b23fb6b4becdac9))
* initial ledger MVP — hash-chained event ingest, timeline UI, demo mode ([061b350](https://github.com/ketriumlabs/agent-activity-ledger/commit/061b3502b9a06d01780852d5144ee248a902a95c))


### Bug Fixes

* catch raw HTTPException (malformed JSON body, 405 Allow header) ([2d77687](https://github.com/ketriumlabs/agent-activity-ledger/commit/2d776874a1e983bd38c5f5ea2a65f5a708460b50))
* schemathesis-found API contract bugs; add fuzz testing to CI ([8005042](https://github.com/ketriumlabs/agent-activity-ledger/commit/8005042ed6f0af8ed22aa651eddac61dfc193311))


### Documentation

* add README badges; fix docker compose demo mode default ([1077ea8](https://github.com/ketriumlabs/agent-activity-ledger/commit/1077ea8146aa694f4b698ebcf3212e814d6fc2fe))

## [Unreleased]

### Added
- Initial scaffold: `agent-event.v0` schema, hash-chain core, SQLite store,
  ingest/query/verify API, timeline UI, demo mode, Claude Code + LangChain
  integrations, MCP self-report server.
- Schemathesis fuzz testing of the live OpenAPI surface, wired into CI.
- `.pre-commit-config.yaml` (ruff, ruff-format, mypy) — install with
  `pre-commit install`.
- `uv.lock` committed for reproducible installs; CI now fails if it drifts
  from `pyproject.toml` (`uv lock --check`).
- Release automation: `release-please` opens the version-bump PR; on
  publish, `publish.yml` builds the sdist/wheel and publishes to PyPI via
  Trusted Publishing (OIDC, no stored token), and builds/pushes a
  multi-arch (amd64+arm64) Docker image to
  `ghcr.io/ketriumlabs/agent-activity-ledger` tagged `latest`/`X.Y.Z`/`X.Y`.
  Both the PyPI artifacts and the Docker image get build-provenance
  attestations (`actions/attest-build-provenance`); the Docker image also
  gets an SPDX SBOM (syft).
- OpenSSF Scorecard workflow (weekly + on push to main), results published
  to the Scorecard API and uploaded to code scanning.
- README badges (CI, PyPI, Docker/GHCR, OpenSSF Scorecard, license).
- `ledger import-claude-code`: a pull-based counterpart to the push-based
  Claude Code hook integration. Reads tool-use activity directly out of
  Claude Code's own local session transcripts
  (`~/.claude/projects/**/*.jsonl`) and imports it into the ledger — no
  hooks config needed. Idempotent by construction: each event's dedup key
  is the transcript's own stable tool_use id, so re-running only imports
  new activity. Verified against real local transcript data (134k+ events
  across this machine's actual Claude Code history), including that the
  hash chain still verifies clean afterward and a second run correctly
  found zero duplicates.

### Fixed
- `sys.stdout.reconfigure(encoding="utf-8")` for Windows-console output was
  only ever wired into `main()`, but the installed `ledger` console script
  (per `pyproject.toml`) calls the Typer `app` object directly and never
  goes through `main()` — so the fix was dead code for the actual CLI.
  Moved to module import time. Found while testing `ledger verify`'s
  output for real on Windows, not by inspection.
- `docker compose up`, as literally documented in the README quickstart,
  didn't actually start in demo mode (`compose.yaml` defaulted `DEMO` to
  empty) — unlike the `docker run -e DEMO=1 ...` one-liner right above it.
  `compose.yaml` now defaults to demo mode too; run `DEMO=0 docker compose
  up` for a real instance. Found by walking the quickstart end-to-end.
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
- A malformed (syntactically broken, not just semantically invalid) JSON
  request body was rejected by Starlette itself before reaching our code,
  bypassing our RFC 9457 problem+json handlers entirely; added a handler
  for the underlying `HTTPException` (also documented the resulting 400 on
  `POST /v1/events`, which FastAPI doesn't auto-document since it's not one
  of our own declared responses). Found by schemathesis running in CI — a
  different random seed than any of my local runs had hit.
- The fix above initially dropped the RFC 9110-required `Allow` header
  that Starlette normally attaches to a 405 Method Not Allowed response,
  since building a response from scratch doesn't carry it over; caught by
  re-running schemathesis immediately after the first fix landed.
