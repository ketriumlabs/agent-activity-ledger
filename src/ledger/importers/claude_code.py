"""Import tool-use activity from Claude Code's own local session
transcripts (~/.claude/projects/**/*.jsonl) into the ledger.

This is a *pull*-based counterpart to integrations/claude-code/, which is
push-based (a hook posts each event as it happens). This importer instead
reads what Claude Code already recorded locally, for backfilling history
or for setups where wiring up the hook isn't practical.

Transcript format (reverse-engineered from real local files, not
documented publicly): one JSON object per line. Lines with
`type == "assistant"` carry a `message.content` array; entries in there
with `type == "tool_use"` are the actual actions — a tool name, its
input, and a globally-unique `id` (e.g. `toolu_01Ab2C...`) that makes a
natural, stable idempotency key.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

from ledger.core.events import Action, ActionType, Actor, EventIn, Source

DEFAULT_TRANSCRIPTS_DIR = Path.home() / ".claude" / "projects"

# Anything not listed here maps to "custom" — deliberately conservative:
# only tools whose purpose is unambiguous get a specific ActionType.
_ACTION_TYPE_BY_TOOL: dict[str, ActionType] = {
    "Write": "file.write",
    "Edit": "file.write",
    "NotebookEdit": "file.write",
    "WebFetch": "http.request",
    "WebSearch": "http.request",
}


class ImportedEvent(NamedTuple):
    event: EventIn
    idempotency_key: str


def _verb_for(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name in ("Write", "Edit", "NotebookEdit", "Read"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return f"{tool_name}: {path}" if path else tool_name
    if tool_name == "Bash":
        desc = tool_input.get("description")
        command = tool_input.get("command", "")
        return desc or f"Ran: {command}"
    return f"Used {tool_name}"


def _target_for(tool_input: dict[str, Any]) -> str | None:
    target = (
        tool_input.get("file_path")
        or tool_input.get("notebook_path")
        or tool_input.get("command")
        or tool_input.get("url")
        or tool_input.get("pattern")
    )
    if target is None:
        return None
    return str(target)[:500]


def _tool_use_to_event(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str,
    ts: str,
    session_id: str,
    model: str | None,
) -> ImportedEvent:
    event = EventIn(
        ts=ts,  # type: ignore[arg-type]  # pydantic coerces the ISO string
        actor=Actor(agent="claude-code", session=session_id, model=model),
        action=Action(
            type=_ACTION_TYPE_BY_TOOL.get(tool_name, "custom"),
            verb=_verb_for(tool_name, tool_input)[:500],
        ),
        target=_target_for(tool_input),
        source=Source(integration="claude-code-transcript-import"),
        metadata={"tool": tool_name},
    )
    return ImportedEvent(event=event, idempotency_key=tool_use_id)


def iter_transcript_files(root: Path = DEFAULT_TRANSCRIPTS_DIR) -> Iterator[Path]:
    if not root.exists():
        return
    yield from sorted(root.rglob("*.jsonl"))


def parse_transcript(path: Path) -> Iterator[ImportedEvent]:
    """Yield one ImportedEvent per tool_use block found in an assistant
    message. Malformed lines are skipped, not fatal — a transcript file is
    append-only application data we don't control, and one bad line
    shouldn't sink import of the rest of a session's history.
    """
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "assistant":
                continue
            message = record.get("message", {})
            content = message.get("content")
            if not isinstance(content, list):
                continue
            ts = record.get("timestamp")
            session_id = record.get("sessionId")
            model = message.get("model")
            if not ts or not session_id:
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name")
                tool_use_id = block.get("id")
                tool_input = block.get("input")
                if not tool_name or not tool_use_id or not isinstance(tool_input, dict):
                    continue
                yield _tool_use_to_event(tool_name, tool_input, tool_use_id, ts, session_id, model)


def iter_all(root: Path = DEFAULT_TRANSCRIPTS_DIR) -> Iterator[ImportedEvent]:
    for path in iter_transcript_files(root):
        yield from parse_transcript(path)
