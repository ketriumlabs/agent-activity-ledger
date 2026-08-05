"""ledger-mcp — an MCP stdio server letting agents self-report events into
their own local ledger via a `log_event` tool.

Requires the `mcp` extra: pip install "agent-activity-ledger[mcp]"
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

LEDGER_URL = os.environ.get("LEDGER_URL", "http://127.0.0.1:8420")
LEDGER_API_KEY = os.environ.get("LEDGER_API_KEY", "")


def _post_event(payload: dict[str, Any]) -> dict[str, Any]:
    resp = httpx.post(
        f"{LEDGER_URL}/v1/events",
        json=payload,
        headers={"Authorization": f"Bearer {LEDGER_API_KEY}"},
        timeout=10.0,
    )
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result


def build_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "ledger-mcp requires the 'mcp' extra. Install with: "
            'pip install "agent-activity-ledger[mcp]"'
        ) from exc

    server = FastMCP("agent-activity-ledger")

    @server.tool()
    def log_event(
        agent: str,
        action_type: str,
        verb: str,
        target: str | None = None,
        amount_value: float | None = None,
        amount_currency: str | None = None,
        justification: str | None = None,
    ) -> dict[str, Any]:
        """Log an action this agent just took to the local Agent Activity Ledger."""
        payload: dict[str, Any] = {
            "ts": datetime.now().astimezone().isoformat(),
            "actor": {"agent": agent},
            "action": {"type": action_type, "verb": verb},
            "source": {"integration": "mcp"},
        }
        if target:
            payload["target"] = target
        if justification:
            payload["justification"] = justification
        if amount_value is not None and amount_currency:
            payload["amount"] = {
                "value": float(Decimal(str(amount_value))),
                "currency": amount_currency,
            }
        return _post_event(payload)

    return server


def main() -> None:
    server = build_server()
    server.run()


if __name__ == "__main__":
    main()
