from __future__ import annotations

from dataclasses import dataclass

from domain.shared.user_id import UserId


@dataclass(frozen=True, slots=True)
class Actor:
    """The signed-in caller for this request (id, roles, permissions)."""

    user_id: UserId
    email: str
    roles: frozenset[str]
    permissions: frozenset[str]
    is_superuser: bool

    def has_permission(self, permission: str) -> bool:
        """True if the caller may perform this permission (superuser always)."""
        if self.is_superuser:
            return True
        return permission in self.permissions
