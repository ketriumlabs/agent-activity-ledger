"""Narrow Schemathesis exceptions for values that HTTP cannot represent as typed."""

import schemathesis


@schemathesis.hook
def filter_failure(ctx, failure, case, response) -> bool:
    """Ignore only a generated non-string Idempotency-Key type mismatch.

    HTTP header field values arrive as strings. Schemathesis may generate a
    non-string OpenAPI value, but its HTTP client serializes that value to text
    before sending it; the server cannot distinguish it from a valid textual
    key. Other invalid headers, parameters, bodies, and checks stay covered.
    """
    return not (
        failure.title == "API accepted schema-violating request"
        and case.method == "POST"
        and case.path == "/v1/events"
        and "parameter `Idempotency-Key` in header" in failure.message
        and "incorrect type" in failure.message.lower()
    )
