#!/usr/bin/env python
"""CI script: validates the documented schema examples and every fixture under
tests/fixtures/integrations/ against schema/agent-event.v0.json. This is the
contract test that protects killcord/context-firewall's emitted payloads."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).parent.parent
SCHEMA_PATH = ROOT / "schema" / "agent-event.v0.json"
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "integrations"


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)

    if not FIXTURES_DIR.exists():
        print(f"No fixtures directory at {FIXTURES_DIR} — nothing to validate.")
        return 0

    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )

    failures = 0
    fixtures = list(FIXTURES_DIR.glob("*.json"))
    for fixture in fixtures:
        payload = json.loads(fixture.read_text())
        try:
            validator.validate(payload)
            print(f"OK   {fixture.relative_to(ROOT)}")
        except jsonschema.ValidationError as exc:
            print(f"FAIL {fixture.relative_to(ROOT)}: {exc.message}")
            failures += 1

    print(f"\n{len(fixtures)} fixture(s) checked, {failures} failure(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
