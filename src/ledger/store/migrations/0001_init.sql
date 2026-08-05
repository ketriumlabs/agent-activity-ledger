CREATE TABLE IF NOT EXISTS events (
    -- seq is the true insertion-order authority the hash chain and pagination
    -- rely on. `id` (UUIDv7) is only ms-precision-ordered: two events inserted
    -- within the same millisecond can sort in either order by id, which would
    -- silently break the chain's ORDER BY assumption. seq never has that problem.
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,       -- UUIDv7, public identifier
    ts TEXT NOT NULL,              -- client-supplied RFC 3339
    received_at TEXT NOT NULL,     -- server-assigned RFC 3339
    agent TEXT NOT NULL,
    session TEXT,
    model TEXT,
    action_type TEXT NOT NULL,
    verb TEXT NOT NULL,
    target TEXT,
    amount_value TEXT,             -- Decimal stored as string, exact
    amount_currency TEXT,
    justification TEXT,
    source_integration TEXT NOT NULL,
    source_version TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',   -- JSON blob
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    idempotency_key TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_events_id ON events(id);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent);
CREATE INDEX IF NOT EXISTS idx_events_action_type ON events(action_type);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_money ON events(amount_value) WHERE amount_value IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idempotency
    ON events(source_integration, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
