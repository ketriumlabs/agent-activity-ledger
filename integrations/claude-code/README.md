# Claude Code integration

A [PostToolUse hook](https://docs.claude.com/en/docs/claude-code/hooks) that logs
money-touching and side-effecting tool calls to your ledger.

## Setup

1. Copy `log_to_ledger.py` into your project (or `~/.claude/hooks/`).
2. Add to your Claude Code `settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash|WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "python /path/to/log_to_ledger.py"
          }
        ]
      }
    ]
  }
}
```

3. Set two environment variables wherever Claude Code runs:

```bash
export LEDGER_URL="http://127.0.0.1:8420"
export LEDGER_API_KEY="lgr_..."
```

That's it — every matched tool call now shows up in your timeline with the
command/URL as the target and a best-effort human-readable verb.
