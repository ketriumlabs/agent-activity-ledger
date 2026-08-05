"""RFC 9457 (problem+json) error responses."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ProblemError(Exception):
    def __init__(
        self,
        status: int,
        title: str,
        detail: str | None = None,
        type_: str = "about:blank",
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.type_ = type_
        super().__init__(detail or title)

    def to_response(self) -> JSONResponse:
        body = {"type": self.type_, "title": self.title, "status": self.status}
        if self.detail:
            body["detail"] = self.detail
        return JSONResponse(
            status_code=self.status,
            content=body,
            media_type="application/problem+json",
        )


async def problem_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)  # guaranteed by add_exception_handler(ProblemError, ...)
    return exc.to_response()


async def request_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI raises RequestValidationError itself for query/path/header
    coercion failures (e.g. `?ts_to=null` failing datetime parsing) —
    those never reach our route handlers, so without this override they'd
    return FastAPI's default `{"detail": [...]}` shape instead of our
    RFC 9457 problem+json format. Found by schemathesis fuzzing the live
    OpenAPI spec, not written speculatively — see CHANGELOG.
    """
    assert isinstance(exc, RequestValidationError)
    return ProblemError(422, "Unprocessable Content", str(exc.errors())).to_response()


def unauthorized(detail: str = "Missing or invalid API key") -> ProblemError:
    return ProblemError(401, "Unauthorized", detail)


def not_found(detail: str = "Resource not found") -> ProblemError:
    return ProblemError(404, "Not Found", detail)


def validation_problem(detail: str) -> ProblemError:
    # 422, not 400: FastAPI auto-documents every endpoint's request-body
    # validation failure as 422 in the generated OpenAPI spec (it adds this
    # response automatically), so a handler-level validation failure must
    # return 422 too or the actual behavior silently diverges from the
    # published contract — exactly what schemathesis's "undocumented status
    # code" check caught when this returned 400.
    return ProblemError(422, "Unprocessable Content", detail)
