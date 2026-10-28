from __future__ import annotations


class DomainError(Exception):
    """Base business error mapped to an HTTP error envelope."""

    def __init__(self, message: str, *, code: str = "domain_error") -> None:
        """Store message and machine-readable code."""
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(DomainError):
    """Input or domain rule failed; includes optional field messages."""

    def __init__(
        self,
        message: str,
        *,
        fields: dict[str, str] | None = None,
        code: str = "validation_failed",
    ) -> None:
        """Store message, code, and per-field error map."""
        super().__init__(message, code=code)
        self.fields = fields or {}


class ConflictError(DomainError):
    """Illegal state change (e.g. deactivate last admin) → HTTP 409."""

    def __init__(self, message: str, *, code: str = "conflict") -> None:
        """Create a conflict error with optional code override."""
        super().__init__(message, code=code)


class NotFoundError(DomainError):
    """Missing or not visible to the caller → HTTP 404."""

    def __init__(
        self,
        message: str = "The requested item was not found.",
        *,
        code: str = "not_found",
    ) -> None:
        """Create a not-found error with optional message/code."""
        super().__init__(message, code=code)


class UnauthorizedError(DomainError):
    """No valid session → HTTP 401."""

    def __init__(
        self,
        message: str = "Authentication required.",
        *,
        code: str = "unauthorized",
    ) -> None:
        """Create an unauthorized error with optional message/code."""
        super().__init__(message, code=code)


class ForbiddenError(DomainError):
    """Authenticated but missing permission → HTTP 403."""

    def __init__(
        self,
        message: str = "You do not have permission for this action.",
        *,
        code: str = "forbidden",
    ) -> None:
        """Create a forbidden error with optional message/code."""
        super().__init__(message, code=code)


class RateLimitError(DomainError):
    """Too many attempts (e.g. login) → HTTP 429."""

    def __init__(
        self,
        message: str = "Too many attempts. Try again later.",
        *,
        code: str = "rate_limited",
    ) -> None:
        """Create a rate-limit error with optional message/code."""
        super().__init__(message, code=code)
