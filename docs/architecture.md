# Architecture

```
 agents ──HTTP POST──▶ ┌─────────────────────────────┐
 (hooks, callbacks,    │  FastAPI service            │
  MCP self-report)     │  ├─ /v1/events  (ingest)    │
                       │  ├─ /v1/events  (query)     │──▶ SQLite (WAL)
                       │  ├─ /v1/verify  (chain)     │     /data/ledger.db
                       │  ├─ /healthz                │
                       │  └─ /  (timeline UI, Jinja2 │
                       │        + htmx, no SPA)      │
                       └──────────┬──────────────────┘
                                  └─ digest scheduler (APScheduler → SMTP)
```

Single process, single container, single SQLite file — see [plan.md](../plan.md)
for the reasoning. Package layout:

```
src/ledger/
├── api/       FastAPI routers: ingest, query, verify, health, app factory
├── core/      hash chain, canonical JSON (RFC 8785), event models — no I/O
├── store/     SQLite repository, migrations, API key management
├── ui/        Jinja2 timeline template + static CSS
├── digest/    email rendering + APScheduler wiring
├── mcp/       ledger-mcp stdio server (optional extra)
├── demo/      seed-data generator for --demo mode
└── cli.py     ledger serve|verify|rotate-key|demo
```

## The seq vs id distinction

The `events` table has two identifier columns:

- `seq` — an `INTEGER PRIMARY KEY AUTOINCREMENT`. The **true insertion-order
  authority**. The hash chain and pagination are ordered by this internally.
- `id` — a UUIDv7, the **public identifier** returned to API clients.

UUIDv7 is only time-ordered at millisecond granularity. Two events inserted
in the same millisecond (routine under any real ingest load, and guaranteed
during demo-data seeding) can sort in either order when compared as strings.
Early in development this repo shipped a bug where the chain and pagination
both used `ORDER BY id`, which meant the demo dataset — several events
inserted in a tight loop — intermittently failed `GET /v1/verify` with a
false-positive tamper report. `seq` exists specifically so ordering never
depends on wall-clock precision. See `tests/test_repository.py::test_rapid_inserts_within_same_millisecond_preserve_chain_order`
for the regression test.
