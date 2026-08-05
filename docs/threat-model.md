# Threat model

This document states plainly what the ledger protects against and what it
does not. Overclaiming here would defeat the point of an audit tool.

## What the hash chain proves

Each event's `hash` is `SHA-256(canonical_json(event) || prev_hash)`. Re-walking
the chain (`GET /v1/verify` or `ledger verify`) recomputes every hash and
reports the first entry where the recomputed value diverges from what's
stored.

**This proves tamper-evidence:** if someone edits, deletes, reorders, or
inserts an event into the SQLite database directly (bypassing the API), the
chain will no longer verify from that point forward.

## What the hash chain does NOT prove

**This is not tamper-proofing.** An attacker with write access to the SQLite
file can:

1. Edit an event,
2. Recompute the hash chain forward from that point,
3. End with a database that verifies cleanly.

The chain only helps if you have an independent record of what the head hash
*should* be at some point in time. **Mitigation:** the digest email (when
configured) includes the chain head hash in its footer — an email in your
inbox is a copy the attacker doesn't control. Periodically noting the head
hash anywhere outside the database (a password manager note, a paper
notebook) achieves the same thing.

## Authentication

- A single API key, argon2-hashed at rest, shown once at creation.
- No rate limiting on the auth check itself in v0.1 — a network-local attacker
  with unlimited attempts could brute-force a weak key. Keys are generated
  with `secrets.token_urlsafe(32)` (256 bits of entropy), which makes this
  impractical, but rate limiting is tracked for a future release.
- `ledger rotate-key` revokes all existing keys and issues a new one — use it
  if a key may have leaked.

## Network exposure

- Binds to `127.0.0.1` by default. Setting `LEDGER_HOST=0.0.0.0` (or running
  the Docker image, which sets this) is an explicit choice to expose the
  service — put it behind your own TLS-terminating reverse proxy and firewall
  rules if you do.
- There is no built-in TLS. This is a self-hosted single-user tool; running
  it on an untrusted network without a reverse proxy is not supported.

## What's out of scope entirely

- **Multi-user isolation.** One API key, one timeline. Don't share the key.
- **Preventing an agent from acting without logging.** The ledger only knows
  about what agents choose to report. It's an audit trail, not a sandbox —
  pair it with [killcord](https://github.com/ketriumlabs/killcord) if you
  need to actually stop an agent, not just record what it did.
- **Detecting compromised agents.** If your agent's own credentials are
  stolen and used directly (not through your normal integration), those
  actions won't appear here unless the attacker also has your ledger API key
  and chooses to log them (they won't).
