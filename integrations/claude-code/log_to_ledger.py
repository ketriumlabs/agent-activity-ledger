#!/usr/bin/env python3
"""Claude Code PostToolUse hook: logs the tool call to Agent Activity Ledger.

Reads the hook payload from stdin (per Claude Code's hook protocol), extracts
a human-readable verb + target, and POSTs an agent-event.v0 record. Never
blocks or fails the tool call — logging errors are swallowed and printed to
stderr only.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

LEDGER_URL = os.environ.get("LEDGER_URL", "http://127.0.0.1:8420")
LEDGER_API_KEY = os.environ.get("LEDGER_API_KEY", "")


def _describe(tool_name: str, tool_input: dict) -> tuple[str, str | None]:
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return f"Ran: {cmd[:200]}", None
    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        return f"Fetched {url}", url
    return f"Used tool {tool_name}", None


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return

    tool_name = payload.get("tool_name", "unknown")
    tool_input = payload.get("tool_input", {})
    verb, target = _describe(tool_name, tool_input)

    event = {
        "ts": datetime.now(timezone.utc).isoformat(),  # noqa: UP017 - keep py<3.11 compatible; standalone hook script
        "actor": {"agent": "claude-code", "session": payload.get("session_id", "")},
        "action": {"type": "custom", "verb": verb},
        "source": {"integration": "claude-code-hook", "version": "0.1.0"},
    }
    if target:
        event["target"] = target

    if not LEDGER_API_KEY:
        return

    try:
        import urllib.request

        req = urllib.request.Request(
            f"{LEDGER_URL}/v1/events",
            data=json.dumps(event).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {LEDGER_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception as exc:  # noqa: BLE001 - hooks must never break the tool call
        print(f"ledger hook: failed to log event: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
