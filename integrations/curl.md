# curl / plain HTTP integration

Any agent framework can log to the ledger with a single POST — no SDK required.

```bash
curl -X POST "$LEDGER_URL/v1/events" \
  -H "Authorization: Bearer $LEDGER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "ts": "2026-08-05T14:03:22Z",
    "actor": {"agent": "my-agent"},
    "action": {"type": "purchase", "verb": "Bought a replacement charger"},
    "target": "amazon.com",
    "amount": {"value": 34.50, "currency": "USD"},
    "justification": "User asked to reorder the same model",
    "source": {"integration": "curl"}
  }'
```

Notes:

- `ts`, `actor.agent`, `action.type`, `action.verb`, and `source.integration` are required — see [`schema/agent-event.v0.json`](../schema/agent-event.v0.json).
- `action.type` must be one of: `purchase`, `email.send`, `message.send`, `file.write`, `http.request`, `auth`, `schedule`, `custom`.
- Set `Idempotency-Key` on anything that might get retried (network hiccups, agent framework retries) — replays with the same key return the original event instead of double-logging it.
- Batch up to 100 events in one request by POSTing a JSON array instead of an object.
