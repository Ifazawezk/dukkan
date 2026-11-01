"""Domain errors raised by services and turned into JSON responses."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.message = message
        self.context = context


class NotFound(DomainError):
    status_code = 404
    code = "not_found"


class Conflict(DomainError):
    status_code = 409
    code = "conflict"


class InsufficientStock(Conflict):
    code = "insufficient_stock"


class PermissionDenied(DomainError):
    status_code = 403
    code = "forbidden"


class InvalidRequest(DomainError):
    status_code = 422
    code = "invalid"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        body: dict[str, Any] = {"detail": exc.message, "code": exc.code}
        if exc.context:
            body["context"] = exc.context
        return JSONResponse(status_code=exc.status_code, content=body)
