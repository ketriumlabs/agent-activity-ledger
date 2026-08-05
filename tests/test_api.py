from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from httpx import ASGITransport

from ledger.api.app import create_app
from ledger.config import Settings
from ledger.store.apikeys import create_key_with_value


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "data", demo=False)


@pytest.fixture
async def client(settings: Settings) -> Iterator[httpx.AsyncClient]:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            create_key_with_value(app.state.conn, "test-key")
            yield c


VALID_EVENT = {
    "ts": "2026-08-05T14:03:22Z",
    "actor": {"agent": "claude-code"},
    "action": {"type": "file.write", "verb": "Wrote a file"},
    "source": {"integration": "test"},
}


async def test_healthz(client: httpx.AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ingest_requires_auth(client: httpx.AsyncClient) -> None:
    resp = await client.post("/v1/events", json=VALID_EVENT)
    assert resp.status_code == 401


async def test_ingest_rejects_bad_key(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/v1/events", json=VALID_EVENT, headers={"Authorization": "Bearer wrong"}
    )
    assert resp.status_code == 401


async def test_ingest_single_event(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/v1/events", json=VALID_EVENT, headers={"Authorization": "Bearer test-key"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["hash"].startswith("sha256:")
    assert body["deduped"] is False


async def test_ingest_rejects_client_supplied_hash(client: httpx.AsyncClient) -> None:
    payload = {**VALID_EVENT, "hash": "sha256:fake"}
    resp = await client.post(
        "/v1/events", json=payload, headers={"Authorization": "Bearer test-key"}
    )
    assert resp.status_code == 400


async def test_ingest_batch(client: httpx.AsyncClient) -> None:
    batch = [VALID_EVENT, VALID_EVENT, {"bad": "event"}]
    resp = await client.post("/v1/events", json=batch, headers={"Authorization": "Bearer test-key"})
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["accepted"]) == 2
    assert len(body["errors"]) == 1


async def test_idempotency_key_dedupes_over_http(client: httpx.AsyncClient) -> None:
    headers = {"Authorization": "Bearer test-key", "Idempotency-Key": "abc-123"}
    first = await client.post("/v1/events", json=VALID_EVENT, headers=headers)
    second = await client.post("/v1/events", json=VALID_EVENT, headers=headers)
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["deduped"] is True


async def test_query_events(client: httpx.AsyncClient) -> None:
    headers = {"Authorization": "Bearer test-key"}
    await client.post("/v1/events", json=VALID_EVENT, headers=headers)
    resp = await client.get("/v1/events", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_verify_empty_chain(client: httpx.AsyncClient) -> None:
    resp = await client.get("/v1/verify", headers={"Authorization": "Bearer test-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["length"] == 0


async def test_verify_after_inserts(client: httpx.AsyncClient) -> None:
    headers = {"Authorization": "Bearer test-key"}
    for _ in range(5):
        await client.post("/v1/events", json=VALID_EVENT, headers=headers)
    resp = await client.get("/v1/verify", headers=headers)
    body = resp.json()
    assert body["ok"] is True
    assert body["length"] == 5


async def test_timeline_ui_renders(client: httpx.AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Agent Activity Ledger" in resp.text
