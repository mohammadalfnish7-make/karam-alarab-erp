from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from domain.identity.events import (
    UserDeactivated,
    UserPasswordChanged,
    UserRegistered,
    UserRolesChanged,
)
from domain.shared.domain_error import ConflictError, ValidationError
from domain.shared.domain_event import DomainEvent
from domain.shared.user_id import UserId

_ROLE_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass
class User:
    """Staff user aggregate: credentials, roles, and active flag."""

    id: UserId
    email: str
    password_hash: str
    is_active: bool
    role_names: set[str]
    created_at: datetime
    updated_at: datetime
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def register(
        cls,
        *,
        email: str,
        password_hash: str,
        role_names: set[str],
        now: datetime,
        user_id: UserId | None = None,
    ) -> User:
        """Create a new active user with roles and emit UserRegistered."""
        normalized = _normalize_email(email)
        if not password_hash:
            raise ValidationError(
                "Password hash is required.",
                fields={"password": "Password hash is required."},
            )
        roles = _normalize_roles(role_names)
        user = cls(
            id=user_id or UserId.generate(),
            email=normalized,
            password_hash=password_hash,
            is_active=True,
            role_names=roles,
            created_at=now,
            updated_at=now,
        )
        user._events.append(
            UserRegistered(
                aggregate_id=str(user.id),
                email=user.email,
                roles=tuple(sorted(user.role_names)),
            )
        )
        return user

    def change_password(self, password_hash: str, *, now: datetime) -> None:
        """Replace the password hash and emit UserPasswordChanged."""
        if not password_hash:
            raise ValidationError(
                "Password hash is required.",
                fields={"password": "Password hash is required."},
            )
        self.password_hash = password_hash
        self.updated_at = now
        self._events.append(
            UserPasswordChanged(aggregate_id=str(self.id), email=self.email)
        )

    def assign_roles(self, role_names: set[str], *, now: datetime) -> None:
        """Replace the user's roles and emit UserRolesChanged."""
        self.role_names = _normalize_roles(role_names)
        self.updated_at = now
        self._events.append(
            UserRolesChanged(
                aggregate_id=str(self.id),
                email=self.email,
                roles=tuple(sorted(self.role_names)),
            )
        )

    def deactivate(self, *, now: datetime, remaining_admins: int) -> None:
        """Deactivate the user; refuse if this is the last active admin."""
        if "admin" in self.role_names and remaining_admins <= 1:
            raise ConflictError("Cannot deactivate the last remaining admin.")
        if not self.is_active:
            return
        self.is_active = False
        self.updated_at = now
        self._events.append(
            UserDeactivated(aggregate_id=str(self.id), email=self.email)
        )

    def activate(self, *, now: datetime) -> None:
        """Mark the user active again so they can sign in."""
        self.is_active = True
        self.updated_at = now

    def pull_events(self) -> list[DomainEvent]:
        """Return and clear pending domain events after a successful save."""
        events = list(self._events)
        self._events.clear()
        return events


def _normalize_email(email: str) -> str:
    """Lowercase/trim email and reject obviously invalid values."""
    value = email.strip().lower()
    if "@" not in value or len(value) < 3:
        raise ValidationError(
            "Email must be a valid address.",
            fields={"email": "Email must be a valid address."},
        )
    return value


def _normalize_roles(role_names: set[str]) -> set[str]:
    """Require at least one role and enforce lowercase name format."""
    if not role_names:
        raise ValidationError(
            "At least one role is required.",
            fields={"roles": "At least one role is required."},
        )
    cleaned: set[str] = set()
    for name in role_names:
        value = name.strip().lower()
        if not _ROLE_NAME.match(value):
            raise ValidationError(
                f"Invalid role name: {name}.",
                fields={"roles": f"Invalid role name: {name}."},
            )
        cleaned.add(value)
    return cleaned
