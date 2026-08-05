# Contributing to Agent Activity Ledger

Thanks for considering a contribution. This project is small and scoped on purpose — see the [MVP cut-line in plan.md](plan.md#product-scope) before proposing large features.

## Dev setup (5 commands)

```bash
git clone https://github.com/ketriumlabs/agent-activity-ledger.git
cd agent-activity-ledger
uv venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"
pytest
```

Optionally install the pre-commit hooks so `ruff`/`mypy` run automatically on `git commit`:

```bash
pre-commit install
```

## Running the ledger locally

```bash
ledger serve --demo
```

Opens on `http://127.0.0.1:8420` with a seeded fake week of agent activity.

## Before you open a PR

- `ruff check . && ruff format --check .`
- `mypy src/ledger`
- `pytest --cov` (core/store logic should stay above 85% coverage)
- Update `CHANGELOG.md` under `[Unreleased]`
- If you touched `schema/agent-event.v0.json`, it must remain **additive-only** — this schema is a cross-project contract (see [plan.md §Data model](plan.md#data-model--ketrium-agent-event-v0-the-portfolio-wide-contract)). Breaking changes require a new `v1` file, not an edit to `v0`.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`. PRs are squash-merged, so your branch history can be messy — the squash commit message is what matters.

## Adding an integration

New integrations (a new agent framework hook/callback) live under `integrations/<name>/`. They must:
1. Emit valid `agent-event.v0` payloads (there's a CI check for this).
2. Ship a short README showing the one-line setup.
3. Come with a recorded example (a JSON fixture of what it sends) under `tests/fixtures/integrations/`.

## Questions

Open a [Discussion](../../discussions) rather than an issue for open-ended questions.
