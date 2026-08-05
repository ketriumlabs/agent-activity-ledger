# Agent Activity Ledger — plan.md

**Verdict:** ✅ Build — clearest gap. Risk: Low. Effort-to-payoff: Best.

**One-liner:** A self-hosted "bank statement" for everything your AI agents did on your behalf.

## Pressure test

- **Prior art:** The space is crowded at the *enterprise* end — Maxim AI, AgentAudit, ARMO, and others all sell agent audit logging as compliance infrastructure for companies. Every result found targets security teams and engineers.
- **The gap is real:** Nothing found targets the individual or small business — a person whose agents book travel, send emails, and make purchases, and who wants one clean human-readable timeline. The "minimum viable audit trail" framing exists in enterprise literature but no consumer product ships it.
- **Risks:**
  1. Adoption depends on agents actually logging to it — mitigate by shipping ready-made hooks for Claude Code (hooks), OpenClaw, LangChain callbacks, and a plain HTTP POST anyone can add in one line.
  2. Enterprise players could move down-market — but their DNA is compliance sales, not `docker run`.

## Product scope

### MVP (v0.1.0)

- One user, one API key (rotatable), one timeline.
- Ingest API (single + batch), tamper-evident hash chain, verify endpoint + CLI.
- Timeline web UI with filters (agent, date range, action type, money-touching) — money actions visually loud.
- Daily/weekly digest email (optional SMTP config).
- Demo mode (`--demo`): seeds a realistic fake week of agent activity.
- Integrations: Claude Code hook, LangChain callback, MCP self-report server, curl one-liner.

### Non-goals (v0.1 cut-line — say no in issues, point here)

Multi-user/orgs, OAuth/SSO, mobile app, real-time websockets, retention policies, analytics dashboards, alerting rules (killcord's job), log shipping to external SIEMs.

## Architecture

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

- **Single process, single container, single SQLite file.** This is the product's identity — resist anything that adds a second moving part.
- UI is server-rendered (Jinja2 + htmx + a small hand-written CSS file). No frontend build step, no node_modules in this repo.
- MCP self-report server ships as a separate small entrypoint (`ledger-mcp`) in the same package, speaking stdio, POSTing to the ledger.

## Data model — Ketrium Agent Event v0 (the portfolio-wide contract)

Published as JSON Schema (draft 2020-12) at `schema/agent-event.v0.json`. **This repo owns the schema**; killcord and context-firewall emit it and CI-validate their payloads against it. Versioned by filename (`v0`, `v1`); additive changes only within a version.

```jsonc
{
  "id": "01937b2e-...",            // server-assigned UUIDv7 (time-ordered)
  "ts": "2026-08-05T14:03:22Z",     // RFC 3339, client-supplied; server records received_at too
  "actor": {
    "agent": "claude-code",         // required — human-recognizable agent name
    "session": "sess_abc",          // optional
    "model": "claude-fable-5"       // optional
  },
  "action": {
    "type": "purchase",             // enum: purchase | email.send | message.send | file.write |
                                    //       http.request | auth | schedule | custom
    "verb": "Booked flight BLR→DEL" // required — one human-readable sentence
  },
  "target": "makemytrip.com",       // what/who was acted on
  "amount": { "value": 129.99, "currency": "USD" },   // optional — presence marks "money-touching"
  "justification": "User asked: 'book the cheapest Tuesday flight'",  // instruction citation
  "source": { "integration": "claude-code-hook", "version": "0.1.0" },
  "metadata": {},                   // free-form, size-capped (8 KB)
  "prev_hash": "sha256:…",          // chain fields, server-computed
  "hash": "sha256:…"
}
```

**Hash chain:** `hash = SHA-256(canonical_json(event minus hash/prev_hash) || prev_hash)`, canonical JSON per RFC 8785 (JCS). Genesis entry uses a fixed sentinel. `/v1/verify` re-walks the chain and reports first divergence; `ledger verify` CLI does the same offline against the SQLite file. **Honest threat model in README:** the chain proves *tamper-evidence* (edits are detectable), not *tamper-proofing* — an attacker with DB write access can rewrite the whole chain; periodic exported chain-head checkpoints (printed in digest emails) are the mitigation.

## API design

- `POST /v1/events` — single object or array (max 100). Headers: `Authorization: Bearer <key>`, `Idempotency-Key` (optional, dedupe window 24h). Returns 201 with assigned ids/hashes, 207 for partial batch validation failures.
- `GET /v1/events?agent=&type=&from=&to=&money=true&cursor=&limit=` — keyset pagination on UUIDv7.
- `GET /v1/verify` — chain status `{ok, length, head_hash, first_bad_id?}`.
- `GET /healthz` — liveness; `GET /` — timeline UI.
- Errors follow RFC 9457 (problem+json). OpenAPI served at `/docs` (FastAPI freebie) — the ingest API doubles as its own integration doc.
- API key: generated on first boot, printed once, stored argon2-hashed. `ledger rotate-key` CLI.

## Tech stack (decisions, not options)

| Concern | Choice | Why |
|---|---|---|
| Language/runtime | Python 3.12 | Shares ecosystem with killcord/provenance-stamp; one toolchain across the portfolio's Python repos |
| Web framework | FastAPI + Uvicorn | OpenAPI for free — the ingest API is the product surface |
| Storage | SQLite (WAL mode), raw `sqlite3` + thin repository layer | Zero-dependency identity; no ORM weight for one table |
| UI | Jinja2 + htmx + hand CSS | No build step, hackable by contributors |
| Scheduler | APScheduler (in-process) | Digest emails without cron/celery |
| Packaging | hatchling build backend, uv for dev + lockfile (`uv.lock` committed — this is an app) | Modern, fast, reproducible |

## Repository layout

```
agent-activity-ledger/
├── src/ledger/
│   ├── api/            # FastAPI routers (ingest, query, verify)
│   ├── core/           # hash chain, canonical JSON, event validation
│   ├── store/          # SQLite repository, migrations (numbered .sql, applied at boot)
│   ├── ui/             # Jinja2 templates, static/
│   ├── digest/         # email rendering + scheduler
│   ├── mcp/            # ledger-mcp stdio server
│   ├── demo/           # seed-data generator
│   └── cli.py          # ledger serve|verify|rotate-key|demo
├── schema/agent-event.v0.json
├── integrations/
│   ├── claude-code/    # hook script + settings snippet
│   ├── langchain/      # callback handler (published as extra: ledger[langchain])
│   └── curl.md
├── tests/              # unit + api (httpx) + property (hypothesis: chain invariants)
├── docs/               # architecture.md, threat-model.md, integrations/
├── Dockerfile, compose.yaml
└── community files (see standards below)
```

## Engineering & open-source standards

### License & legal

- **Apache-2.0** (permissive, explicit patent grant, enterprise-friendly — matters for trust-layer positioning). `LICENSE` at root, `license = "Apache-2.0"` in `pyproject.toml`. Copyright line: `Copyright (c) 2026 Ketrium Labs`. No CLA; DCO optional, never gating.

### Community files (all present before the first feature commit)

| File | Standard |
|---|---|
| `README.md` | Structure below |
| `CONTRIBUTING.md` | Dev setup in ≤5 commands (`uv sync`, `uv run pytest`…), test instructions, PR expectations, commit convention |
| `CODE_OF_CONDUCT.md` | Contributor Covenant v2.1 |
| `SECURITY.md` | Private reporting via GitHub Security Advisories; acknowledge ≤72h, fix-or-plan ≤14 days for HIGH+ |
| `CHANGELOG.md` | Keep a Changelog format, maintained by release automation |
| `.github/ISSUE_TEMPLATE/` | `bug_report.yml`, `feature_request.yml` (YAML form templates) |
| `.github/PULL_REQUEST_TEMPLATE.md` | Checklist: tests, docs, changelog |
| `.github/dependabot.yml` | Weekly, grouped minor/patch, pip + github-actions ecosystems |
| `.editorconfig`, `.gitignore` | 4-space Python, LF, final newline; `.env*`, `/data` ignored |

Repo settings: Discussions on, squash-merge only, branch protection on `main` (CI required), `good first issue` / `help wanted` labels seeded with 3–5 real issues before launch.

### README structure (reader reaches a working demo in <5 minutes)

1. One-liner + ≤10s demo GIF → 2. badges (CI, PyPI, Docker, license) → 3. **Quickstart** (`docker run ghcr.io/ketriumlabs/agent-activity-ledger --demo`) → 4. why/what (bullets) → 5. integration examples → 6. configuration table → 7. **security model incl. what it does NOT protect against** → 8. roadmap/contributing/license links.

### Versioning & releases

- **SemVer** from `0.1.0`; pre-1.0 breaking changes bump minor and get a **BREAKING** changelog entry.
- **Conventional Commits**; maintainer normalizes on squash-merge — no bot nagging contributors.
- **release-please** → GitHub Release → **PyPI Trusted Publishing** (OIDC, no long-lived tokens).
- Docker image to **GHCR** (`ghcr.io/ketriumlabs/agent-activity-ledger`), tags `latest`/`X.Y.Z`/`X.Y`, multi-arch (amd64+arm64) via buildx.
- **Artifact attestations** (`actions/attest-build-provenance`) + SBOM (syft) attached to releases; signed tags.

### CI/CD (GitHub Actions)

`ci.yml` on PR + main: ruff (lint+format check) → mypy --strict on `src/` → pytest with coverage (target ≥85% on `core/` and `store/`) on Python 3.12/3.13, ubuntu → Docker build + demo smoke test. `codeql.yml` weekly + on PR. `pip-audit` warn-only pre-1.0. Actions pinned to SHA, minimal `permissions:`; release workflow separate with `id-token: write` scoped to the publish job. OpenSSF Scorecard post-launch, target ≥7.0.

### Toolchain

`src/` layout; **ruff** (lint + format), **mypy --strict**, **pytest** + `pytest-cov`, **hypothesis** for chain invariants, **pre-commit** hooks (ruff, ruff-format, mypy).

### Docker standard

Multi-stage → `python:3.12-slim`, **non-root user**, `HEALTHCHECK` on `/healthz`, `VOLUME /data`. Zero required config — safe defaults, env-var overrides (12-factor), effective config printed at startup with secrets redacted. Binds `127.0.0.1` by default; `0.0.0.0` is an explicit opt-in (`LEDGER_HOST`). `compose.yaml` in root.

## Testing strategy

- **Property tests (hypothesis):** chain verification detects any single-field mutation; canonical JSON stable across dict ordering.
- **API tests:** auth, idempotency dedupe, batch partial failure, pagination edges — httpx against the app, plus **schemathesis** fuzzing generated from the OpenAPI spec.
- **Golden/contract tests:** `schema/agent-event.v0.json` validates documented examples; every `integrations/` payload validated against the schema in CI (protects killcord/context-firewall downstream).
- **Smoke test in CI:** build image, run `--demo`, curl `/healthz` + `/v1/verify`.

## Build plan — milestones

Expanded from the original 7-day sketch; each milestone has a Definition of Done.

**M0 — Scaffold (day 1).** Repo with all community files, CI green on empty package, Dockerfile skeleton. *DoD: `uv run pytest` and docker build pass in CI.*

**M1 — Core + schema (days 1–2).** Event schema frozen as v0 JSON Schema; hash chain + canonical JSON; SQLite store with migrations. *DoD: property tests green; `ledger verify` works on a hand-built DB.*

**M2 — Ingest API (day 2).** POST with auth, idempotency, batch; verify endpoint. *DoD: schemathesis run clean; README curl example works.*

**M3 — Timeline UI + digest (days 3–4).** Filterable timeline, loud money styling, digest email behind SMTP env vars. *DoD: UI usable at mobile width; digest renders correctly in a real inbox.*

**M4 — Integrations (day 5).** Claude Code hook, LangChain callback, MCP self-report server, curl doc. *DoD: each integration produces a schema-valid event end-to-end in a recorded demo.*

**M5 — Ship kit (day 6).** GHCR image (multi-arch), `--demo` mode, README with GIF, threat-model doc. *DoD: launch checklist below fully ticked.*

**M6 — Launch (day 7).** `v0.1.0` tagged, PyPI + GHCR published with attestations. Show HN: *"I built a bank statement for my AI agents"*; r/selfhosted, r/LocalLLaMA. First comment pre-written: what it is, what it is not (non-goals), the honest tamper-evidence caveat.

### Launch checklist

- [ ] Quickstart verified on a clean machine/fresh container
- [ ] Demo mode + GIF working and embedded in README
- [ ] All community files present; 3–5 `good first issue` items filed
- [ ] `v0.1.0` tagged, release notes, PyPI + GHCR published with attestations
- [ ] Show HN draft reviewed; honest first comment pre-written
- [ ] Respond to every issue/comment within 24h for the first week

## Post-launch (v0.2 groomed by real issues, not speculation)

Likely candidates: retention/archival export (JSONL), read-only share link for a timeline slice, ntfy.sh push on money events (bridges toward killcord), OpenTelemetry ingest translator. Multi-user stays out until demand is loud.

**Maintenance policy (stated in README):** issues triaged weekly; security per SECURITY.md SLO; "maintained, scoped small" — big asks go to Discussions.

## Synergy with other ketriumlabs projects

The log-entry format here doubles as the sink for [killcord](../killcord/plan.md)'s trip events and [context-firewall](../context-firewall/plan.md)'s request log — same schema, shared story across launches. Downstream repos pin a schema version and CI-validate emitted payloads against it.

## Sequence position

**Week 1.** Build this first — lowest risk, fastest to demo, establishes the brand theme for the whole "trust layer for the agent era" campaign.
