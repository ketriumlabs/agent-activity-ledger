# Security Policy

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately via [GitHub Security Advisories](../../security/advisories/new)
for this repository.

## Response SLO

- **Acknowledgement:** within 72 hours.
- **Fix or mitigation plan:** within 14 days for HIGH+ severity findings.

Findings that break the hash-chain tamper-evidence guarantee, bypass API-key
auth, or leak another user's data are always treated as HIGH severity.

## Supported Versions

Only the latest `0.x` minor release is supported pre-1.0. There is no LTS
branch yet.

## Scope

In scope: the `ledger` package (API, store, core, UI, CLI, MCP server) and
the official integrations under `integrations/`. Third-party integrations
built on top of the ingest API are out of scope for this repo.
