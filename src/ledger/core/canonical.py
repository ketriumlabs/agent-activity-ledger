"""RFC 8785 (JCS) canonical JSON serialization.

Used so that hashing an event is deterministic regardless of dict
insertion order, whitespace, or float formatting quirks between
languages/clients.
"""

from __future__ import annotations

import math
from typing import Any

_ESCAPE_MAP = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def _escape_string(s: str) -> str:
    out: list[str] = ['"']
    for ch in s:
        if ch in _ESCAPE_MAP:
            out.append(_ESCAPE_MAP[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _format_number(n: float | int) -> str:
    if isinstance(n, bool):  # bool is a subclass of int — must check first
        raise TypeError("bool is not a valid JCS number")
    if isinstance(n, int):
        return str(n)
    if math.isnan(n) or math.isinf(n):
        raise ValueError("NaN/Infinity are not valid JSON numbers")
    if n == int(n) and abs(n) < 1e15:
        return str(int(n))
    return repr(n)


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _format_number(value)
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        body = ",".join(f"{_escape_string(k)}:{_encode(v)}" for k, v in items)
        return "{" + body + "}"
    raise TypeError(f"Cannot canonicalize value of type {type(value)!r}")


def canonical_json(value: dict[str, Any]) -> bytes:
    """Serialize a JSON-compatible dict to RFC 8785 canonical form, UTF-8 encoded."""
    return _encode(value).encode("utf-8")
