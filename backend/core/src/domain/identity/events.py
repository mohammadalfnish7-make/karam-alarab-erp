from __future__ import annotations

from dataclasses import dataclass

from domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(DomainEvent):
    """A new staff user was created."""

    email: str = ""
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDeactivated(DomainEvent):
    """A staff user was deactivated and can no longer sign in."""

    email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRolesChanged(DomainEvent):
    """A staff user's role set was replaced."""

    email: str = ""
    roles: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordChanged(DomainEvent):
    """A staff user changed their password (sessions should be revoked)."""

    email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class LoginFailed(DomainEvent):
    """A login attempt failed (audit / rate-limit signal)."""

    email: str = ""
    reason: str = ""
