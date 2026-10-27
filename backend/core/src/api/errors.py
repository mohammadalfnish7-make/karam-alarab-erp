from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from domain.shared.domain_error import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)


def _envelope(code: str, message: str, fields: dict[str, str] | None = None) -> dict:
    """Build the standard `{error: {code, message, fields?}}` JSON body."""
    error: dict = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain and validation failures to consistent HTTP error envelopes."""

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return 400 for Pydantic/FastAPI request body validation failures."""
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []) if part != "body")
            fields[loc or "body"] = err.get("msg", "Invalid value.")
        return JSONResponse(
            status_code=400,
            content=_envelope("validation_failed", "Request validation failed.", fields),
        )

    @app.exception_handler(ValidationError)
    async def domain_validation_handler(
        _request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Return 400 for domain ValidationError."""
        return JSONResponse(
            status_code=400,
            content=_envelope(exc.code, exc.message, exc.fields),
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(
        _request: Request,
        exc: UnauthorizedError,
    ) -> JSONResponse:
        """Return 401 when the caller is not authenticated."""
        return JSONResponse(status_code=401, content=_envelope(exc.code, exc.message))

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_request: Request, exc: ForbiddenError) -> JSONResponse:
        """Return 403 when the caller lacks permission."""
        return JSONResponse(status_code=403, content=_envelope(exc.code, exc.message))

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
        """Return 404 when a resource is missing."""
        return JSONResponse(status_code=404, content=_envelope(exc.code, exc.message))

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
        """Return 409 for uniqueness or state conflicts."""
        return JSONResponse(status_code=409, content=_envelope(exc.code, exc.message))

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(_request: Request, exc: RateLimitError) -> JSONResponse:
        """Return 429 when login attempts are throttled."""
        return JSONResponse(status_code=429, content=_envelope(exc.code, exc.message))

    @app.exception_handler(DomainError)
    async def domain_handler(_request: Request, exc: DomainError) -> JSONResponse:
        """Return 400 for any other DomainError subclass."""
        return JSONResponse(status_code=400, content=_envelope(exc.code, exc.message))

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, _exc: Exception) -> JSONResponse:
        """Return a generic 500 without leaking internals."""
        return JSONResponse(
            status_code=500,
            content=_envelope("internal_error", "An unexpected error occurred."),
        )
