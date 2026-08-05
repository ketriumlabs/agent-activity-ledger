"""Renders a plain-text + HTML digest email of recent ledger activity."""

from __future__ import annotations

from ledger.core.events import EventRecord


def render_digest(events: list[EventRecord], period_label: str) -> tuple[str, str]:
    """Returns (text_body, html_body)."""
    money_events = [e for e in events if e.amount is not None]
    total_by_currency: dict[str, float] = {}
    for e in money_events:
        assert e.amount is not None
        total_by_currency[e.amount.currency] = total_by_currency.get(
            e.amount.currency, 0.0
        ) + float(e.amount.value)

    lines = [f"Agent Activity Ledger — {period_label}", "=" * 40, ""]
    if not events:
        lines.append("No activity this period.")
    else:
        lines.append(f"{len(events)} events, {len(money_events)} money-touching.")
        if total_by_currency:
            totals = ", ".join(f"{v:.2f} {c}" for c, v in total_by_currency.items())
            lines.append(f"Total spend: {totals}")
        lines.append("")
        for e in events:
            marker = "$ " if e.amount else "  "
            lines.append(f"{marker}[{e.actor.agent}] {e.action.verb}")
    text_body = "\n".join(lines)

    def _amount_cell(e: EventRecord) -> str:
        if e.amount is None:
            return ""
        return f"{e.amount.value} {e.amount.currency}"

    rows = "".join(
        f"<tr><td>{e.actor.agent}</td><td>{e.action.verb}</td><td>{_amount_cell(e)}</td></tr>"
        for e in events
    )
    html_body = f"""<html><body>
<h2>Agent Activity Ledger — {period_label}</h2>
<p>{len(events)} events, {len(money_events)} money-touching.</p>
<table border="1" cellpadding="6" cellspacing="0">
<tr><th>Agent</th><th>Action</th><th>Amount</th></tr>
{rows}
</table>
</body></html>"""

    return text_body, html_body
