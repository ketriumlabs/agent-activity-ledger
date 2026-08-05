from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "agent-event.v0.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


VALID_EXAMPLES = [
    {
        "ts": "2026-08-05T14:03:22Z",
        "actor": {"agent": "claude-code"},
        "action": {"type": "file.write", "verb": "Wrote src/api/routes.py"},
        "source": {"integration": "claude-code-hook", "version": "0.1.0"},
    },
    {
        "ts": "2026-08-05T14:03:22Z",
        "actor": {"agent": "travel-bot", "session": "sess_abc", "model": "claude-fable-5"},
        "action": {"type": "purchase", "verb": "Booked flight BLR to DEL"},
        "target": "makemytrip.com",
        "amount": {"value": 129.99, "currency": "USD"},
        "justification": "User asked: 'book the cheapest Tuesday flight'",
        "source": {"integration": "langchain"},
        "metadata": {"flight_number": "AI505"},
    },
]

_BASE = {
    "ts": "2026-08-05T14:03:22Z",
    "actor": {"agent": "x"},
    "action": {"type": "custom", "verb": "x"},
    "source": {"integration": "x"},
}

INVALID_EXAMPLES = [
    {},  # missing required fields
    {**_BASE, "ts": "not-a-date"},
    {**_BASE, "actor": {}},  # missing required actor.agent
    {**_BASE, "action": {"type": "not-a-real-type", "verb": "x"}},
    {**_BASE, "unknown_field": True},  # additionalProperties: false
]


def _validate(instance: dict, schema: dict) -> None:
    # format_checker is required for the "date-time" format on ts/received_at
    # to actually be enforced — jsonschema.validate() skips format checks by default.
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    validator.validate(instance)


@pytest.mark.parametrize("example", VALID_EXAMPLES)
def test_valid_examples_pass(schema: dict, example: dict) -> None:
    _validate(example, schema)


@pytest.mark.parametrize("example", INVALID_EXAMPLES)
def test_invalid_examples_fail(schema: dict, example: dict) -> None:
    with pytest.raises(jsonschema.ValidationError):
        _validate(example, schema)


def test_schema_is_valid_json_schema(schema: dict) -> None:
    jsonschema.Draft202012Validator.check_schema(schema)
