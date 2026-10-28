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


def _humanize_pydantic_error(err: dict) -> str:
    """Turn a Pydantic/FastAPI error into a short, readable field message."""
    typ = str(err.get("type", ""))
    ctx = err.get("ctx") or {}
    msg = str(err.get("msg", "Invalid value."))

    if typ == "missing":
        return "This field is required."
    if typ == "string_too_short":
        minimum = ctx.get("min_length", 1)
        return f"Must be at least {minimum} characters."
    if typ == "string_too_long":
        maximum = ctx.get("max_length", 0)
        return f"Must be at most {maximum} characters."
    if typ in {"int_parsing", "int_type"}:
        return "Must be a whole number."
    if typ in {"float_parsing", "float_type"}:
        return "Must be a number."
    if typ in {"bool_parsing", "bool_type"}:
        return "Must be true or false."
    if typ in {"uuid_parsing", "uuid_type"}:
        return "Must be a valid UUID."
    if typ == "list_type":
        return "Must be a list."
    if typ == "greater_than_equal":
        return f"Must be at least {ctx.get('ge', 0)}."
    if typ == "less_than_equal":
        return f"Must be at most {ctx.get('le', 0)}."
    if typ == "extra_forbidden":
        return "Unexpected field."
    if typ.startswith("value_error") or msg.lower().startswith("value error"):
        cleaned = msg.split(",", 1)[-1].strip() if "," in msg else msg
        return cleaned[:1].upper() + cleaned[1:] if cleaned else "Invalid value."
    # Drop noisy pydantic prefixes like "Input should be …"
    if msg.startswith("Input should be"):
        return msg.replace("Input should be", "Must be", 1)
    return msg


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
            fields[loc or "body"] = _humanize_pydantic_error(err)
        return JSONResponse(
            status_code=400,
            content=_envelope(
                "validation_failed",
                "Please fix the highlighted fields and try again.",
                fields,
            ),
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
