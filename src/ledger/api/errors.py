"""RFC 9457 (problem+json) error responses."""

from __future__ import annotations

from fastapi import Request
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


def unauthorized(detail: str = "Missing or invalid API key") -> ProblemError:
    return ProblemError(401, "Unauthorized", detail)


def not_found(detail: str = "Resource not found") -> ProblemError:
    return ProblemError(404, "Not Found", detail)


def validation_problem(detail: str) -> ProblemError:
    return ProblemError(400, "Bad Request", detail)
