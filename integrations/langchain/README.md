# LangChain integration

```bash
pip install "agent-activity-ledger[langchain]"
```

```python
from langchain_callback import LedgerCallbackHandler

handler = LedgerCallbackHandler(
    agent_name="travel-bot",
    ledger_url="http://127.0.0.1:8420",
    api_key="lgr_...",
)

agent_executor.invoke({"input": "book me a flight"}, config={"callbacks": [handler]})
```

Every tool call the agent makes is logged as one `agent-event.v0` record —
`action.type` is set from a best-effort mapping (see `TOOL_TYPE_HINTS` in
`langchain_callback.py`; unmapped tools fall back to `"custom"`), `verb` is the
tool name + a truncated input summary, and `target` is the tool input when it
looks like a URL or domain.
