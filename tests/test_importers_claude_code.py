from __future__ import annotations

from pathlib import Path

from ledger.importers.claude_code import iter_all, iter_transcript_files, parse_transcript
from ledger.store.repository import EventRepository

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "claude_code_transcripts"
SAMPLE = FIXTURE_DIR / "sample.jsonl"


def test_iter_transcript_files_finds_jsonl_recursively() -> None:
    files = list(iter_transcript_files(FIXTURE_DIR))
    assert SAMPLE in files


def test_iter_transcript_files_missing_root_yields_nothing() -> None:
    assert list(iter_transcript_files(FIXTURE_DIR / "does-not-exist")) == []


def test_parse_transcript_extracts_tool_use_events_only() -> None:
    items = list(parse_transcript(SAMPLE))
    # 3 tool_use blocks in the fixture: Write, Bash, Read.
    # The thinking-only assistant line and the malformed line are skipped.
    assert len(items) == 3
    assert {i.idempotency_key for i in items} == {"toolu_01AAA", "toolu_01BBB", "toolu_01CCC"}


def test_parse_transcript_maps_write_to_file_write() -> None:
    items = {i.idempotency_key: i for i in parse_transcript(SAMPLE)}
    write_event = items["toolu_01AAA"].event
    assert write_event.action.type == "file.write"
    assert write_event.target == "/tmp/example.txt"
    assert write_event.actor.agent == "claude-code"
    assert write_event.actor.session == "11111111-1111-1111-1111-111111111111"
    assert write_event.source.integration == "claude-code-transcript-import"


def test_parse_transcript_maps_unknown_tool_to_custom() -> None:
    items = {i.idempotency_key: i for i in parse_transcript(SAMPLE)}
    bash_event = items["toolu_01BBB"].event
    assert bash_event.action.type == "custom"
    assert bash_event.target == "ls -la"
    assert "List files" in bash_event.action.verb


def test_import_is_idempotent_across_repeated_runs(repo: EventRepository) -> None:
    for item in iter_all(FIXTURE_DIR):
        repo.insert(item.event, idempotency_key=item.idempotency_key)
    assert repo.count() == 3

    # Re-running the import (e.g. a second `ledger import-claude-code`)
    # must not double-insert — every event's idempotency key is the
    # transcript's own stable tool_use id.
    for item in iter_all(FIXTURE_DIR):
        repo.insert(item.event, idempotency_key=item.idempotency_key)
    assert repo.count() == 3
