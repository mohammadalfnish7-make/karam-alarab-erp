from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.identity.user import User
from domain.shared.user_id import UserId


class UserRepository(Protocol):
    """Load and save User aggregates."""

    def get(self, user_id: UserId) -> User | None:
        """Find a user by id, or None."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email, or None."""
        ...

    def save(self, user: User) -> None:
        """Insert or update a user and their role links."""
        ...

    def list_users(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        """Return a page of users and the total count."""
        ...

    def count_active_admins(self) -> int:
        """Count active users that hold the admin role."""
        ...


class SessionRecord(Protocol):
    """Shape of a persisted login session row."""

    id: UUID
    user_id: UserId
    token_hash: str
    expires_at: datetime
    created_at: datetime


class SessionRepository(Protocol):
    """Create and revoke server-side sessions."""

    def create(
        self,
        *,
        user_id: UserId,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> UUID:
        """Store a new hashed session token; return its id."""
        ...

    def get_by_token_hash(self, token_hash: str) -> tuple[UUID, UserId, datetime] | None:
        """Look up session id, user, and expiry by hashed token."""
        ...

    def delete(self, session_id: UUID) -> None:
        """Delete one session by id."""
        ...

    def delete_by_token_hash(self, token_hash: str) -> None:
        """Delete the session matching a hashed cookie token."""
        ...

    def delete_all_for_user(self, user_id: UserId) -> None:
        """Revoke every session for a user (e.g. after password change)."""
        ...


class RoleRepository(Protocol):
    """Open RBAC: roles, permission names, and grants."""

    def list_roles(self) -> list[tuple[str, bool, list[str]]]:
        """List roles with superuser flag and granted permission names."""
        ...

    def list_permissions(self) -> list[str]:
        """List all registered permission name strings."""
        ...

    def role_exists(self, name: str) -> bool:
        """True if a role row exists."""
        ...

    def ensure_roles_exist(self, names: set[str]) -> None:
        """Raise if any role name is unknown."""
        ...

    def register_permissions(self, names: list[str]) -> list[str]:
        """Insert missing permission names; return those newly created."""
        ...

    def set_role_permissions(self, role_name: str, permission_names: list[str]) -> None:
        """Replace a role's permission grants."""
        ...

    def permissions_for_roles(self, role_names: set[str]) -> set[str]:
        """Resolve effective permission names for a set of roles."""
        ...

    def is_superuser_role(self, role_name: str) -> bool:
        """True if this role bypasses explicit permission grants."""
        ...

    def user_is_superuser(self, role_names: set[str]) -> bool:
        """True if any of the roles is a superuser role."""
        ...


class PasswordHasher(Protocol):
    """Hash and verify passwords (Argon2 in infrastructure)."""

    def hash(self, password: str) -> str:
        """Hash a plaintext password for storage."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """True if plaintext matches the stored hash."""
        ...


class LoginAttemptStore(Protocol):
    """Track failed logins for rate limiting."""

    def record_failure(self, key: str, *, now: datetime) -> int:
        """Record a failed attempt; return how many are in the window."""
        ...

    def clear(self, key: str) -> None:
        """Clear failures after a successful login."""
        ...

    def recent_failures(self, key: str, *, since: datetime) -> int:
        """Count failures for a key since a timestamp."""
        ...
