"""LangChain callback handler that logs tool calls to Agent Activity Ledger.

Requires: pip install "agent-activity-ledger[langchain]"
"""

from __future__ import annotations

import contextlib
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from langchain_core.callbacks import BaseCallbackHandler

TOOL_TYPE_HINTS = {
    "send_email": "email.send",
    "purchase": "purchase",
    "checkout": "purchase",
    "book": "purchase",
    "schedule": "schedule",
    "calendar": "schedule",
    "message": "message.send",
    "fetch": "http.request",
    "browse": "http.request",
    "search": "http.request",
}

_URL_RE = re.compile(r"https?://[^\s'\"]+")


def _infer_action_type(tool_name: str) -> str:
    lowered = tool_name.lower()
    for hint, action_type in TOOL_TYPE_HINTS.items():
        if hint in lowered:
            return action_type
    return "custom"


def _extract_target(tool_input: str) -> str | None:
    match = _URL_RE.search(tool_input)
    return match.group(0) if match else None


class LedgerCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        agent_name: str,
        ledger_url: str = "http://127.0.0.1:8420",
        api_key: str = "",
        timeout: float = 5.0,
    ) -> None:
        self.agent_name = agent_name
        self.ledger_url = ledger_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=timeout)

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        event = {
            "ts": datetime.now(UTC).isoformat(),
            "actor": {"agent": self.agent_name, "session": str(run_id)},
            "action": {
                "type": _infer_action_type(tool_name),
                "verb": f"Called {tool_name}: {input_str[:200]}",
            },
            "source": {"integration": "langchain", "version": "0.1.0"},
        }
        target = _extract_target(input_str)
        if target:
            event["target"] = target

        if not self.api_key:
            return
        with contextlib.suppress(httpx.HTTPError):  # logging must never break the agent run
            self._client.post(
                f"{self.ledger_url}/v1/events",
                json=event,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
