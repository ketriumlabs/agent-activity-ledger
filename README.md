# Agent Activity Ledger

[![CI](https://github.com/ketriumlabs/agent-activity-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/ketriumlabs/agent-activity-ledger/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agent-activity-ledger)](https://pypi.org/project/agent-activity-ledger/)
[![Docker](https://img.shields.io/badge/ghcr.io-agent--activity--ledger-blue?logo=docker)](https://github.com/ketriumlabs/agent-activity-ledger/pkgs/container/agent-activity-ledger)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/ketriumlabs/agent-activity-ledger/badge)](https://scorecard.dev/viewer/?uri=github.com/ketriumlabs/agent-activity-ledger)
[![License](https://img.shields.io/github/license/ketriumlabs/agent-activity-ledger)](LICENSE)

**A self-hosted bank statement for everything your AI agents did on your behalf.**

Booked a flight. Sent an email. Bought a replacement charger. If your agents act for you, you deserve one clean, tamper-evident timeline of what happened — not a vendor dashboard, not a log file you'll never read.

```bash
docker run -p 8420:8420 -e DEMO=1 ghcr.io/ketriumlabs/agent-activity-ledger
```

Open `http://127.0.0.1:8420` and you'll see a week of realistic fake activity, money-touching actions highlighted.

## Quickstart

```bash
pip install agent-activity-ledger
ledger serve --demo
```

Or with Docker Compose:

```bash
docker compose up
```

Send your first real event:

```bash
curl -X POST http://127.0.0.1:8420/v1/events \
  -H "Authorization: Bearer $LEDGER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "ts": "2026-08-05T14:03:22Z",
    "actor": {"agent": "claude-code"},
    "action": {"type": "file.write", "verb": "Wrote src/api/routes.py"},
    "source": {"integration": "curl"}
  }'
```

## Why

- **Enterprise agent-audit tools exist — Maxim AI, AgentAudit, ARMO — but they're built for security teams, not individuals.** This is the "minimum viable audit trail" for a person or small business whose agents book travel, send emails, and spend money.
- **One user, one API key, one timeline.** No multi-tenant complexity to fight through.
- **Tamper-evident, not tamper-proof — and the README says so.** See [Security model](#security-model) below.

## Integrations

| Integration | Setup |
|---|---|
| Claude Code | Copy [`integrations/claude-code/`](integrations/claude-code) into your hooks config — one line. |
| LangChain | `LedgerCallbackHandler` from [`integrations/langchain/`](integrations/langchain). |
| MCP | `pip install "agent-activity-ledger[mcp]"` then point any MCP client at `ledger-mcp`. |
| Anything else | `POST /v1/events`, see [`integrations/curl.md`](integrations/curl.md). |

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `LEDGER_HOST` | `127.0.0.1` | Bind address — stays local unless you opt in |
| `LEDGER_PORT` | `8420` | Port |
| `LEDGER_DATA_DIR` | `./data` | Where `ledger.db` lives |
| `DEMO` | unset | `1`/`true` seeds fake data and uses a fixed `demo` API key |
| `LEDGER_SMTP_HOST` / `_PORT` / `_USER` / `_PASSWORD` | unset | Enables daily/weekly digest email |
| `LEDGER_DIGEST_TO` | unset | Digest recipient |

## Security model

**What this proves:** each event is chained to the previous one with a SHA-256 hash over its RFC 8785 canonical JSON form. `GET /v1/verify` (or `ledger verify`) re-walks the whole chain and reports the first entry where something doesn't match — any edit to a past event is detectable.

**What this does NOT prove:** this is *tamper-evidence*, not *tamper-proofing*. An attacker with write access to the SQLite file can rewrite the entire chain forward from any point and it will re-verify cleanly. Mitigation: periodically export and store the chain head hash somewhere else (a digest email footer, a note to yourself) — a saved-elsewhere head hash is what turns "detectable if you check" into "detectable, period."

API keys are argon2-hashed at rest and shown once at creation. There is no multi-user isolation — this is a single-user tool by design.

## Roadmap

See [plan.md](plan.md) for the full build plan and post-launch direction (retention export, share links, OpenTelemetry ingest).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache-2.0](LICENSE)
