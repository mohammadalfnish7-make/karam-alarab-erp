from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from application.actor import Actor
from domain.identity.events import LoginFailed
from domain.identity.ports import (
    LoginAttemptStore,
    PasswordHasher,
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from domain.identity.user import User
from domain.shared.clock import Clock
from domain.shared.domain_error import RateLimitError, UnauthorizedError, ValidationError
from domain.shared.user_id import UserId
from support.events import UnitOfWork

LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_MAX_FAILURES = 10
# Precomputed Argon2id hash of a constant string — used only to equalize timing.
DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "MgzXUxaOBS2Cjgm2FPVwhg$qp9Vl9MM2Bgm2K66kCO5N34B5Sr16NP8Jm96Le5APbw"
)


class AuthService:
    """Login, logout, session resolution, and password change."""

    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        roles: RoleRepository,
        attempts: LoginAttemptStore,
        hasher: PasswordHasher,
        clock: Clock,
        uow: UnitOfWork,
        session_ttl_seconds: int,
    ) -> None:
        """Wire identity ports, clock, UoW, and session TTL."""
        self._users = users
        self._sessions = sessions
        self._roles = roles
        self._attempts = attempts
        self._hasher = hasher
        self._clock = clock
        self._uow = uow
        self._session_ttl_seconds = session_ttl_seconds

    def login(self, *, email: str, password: str, client_key: str) -> tuple[str, Actor]:
        """Authenticate; return raw session token + actor (or generic 401)."""
        now = self._clock.now()
        key = f"{client_key}:{email.strip().lower()}"
        since = now - LOGIN_WINDOW
        if self._attempts.recent_failures(key, since=since) >= LOGIN_MAX_FAILURES:
            raise RateLimitError()

        user = self._users.get_by_email(email)
        if user is None or not user.is_active:
            self._hasher.verify(password or "x", DUMMY_HASH)
            self._attempts.record_failure(key, now=now)
            self._uow.collect(
                [
                    LoginFailed(
                        aggregate_id=email.strip().lower(),
                        email=email.strip().lower(),
                        reason="unknown_or_inactive",
                    )
                ]
            )
            self._uow.commit()
            raise UnauthorizedError("Invalid email or password.")

        if not self._hasher.verify(password, user.password_hash):
            self._attempts.record_failure(key, now=now)
            self._uow.collect(
                [
                    LoginFailed(
                        aggregate_id=str(user.id),
                        email=user.email,
                        reason="bad_password",
                    )
                ]
            )
            self._uow.commit()
            raise UnauthorizedError("Invalid email or password.")

        self._attempts.clear(key)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(raw_token)
        expires_at = now + timedelta(seconds=self._session_ttl_seconds)
        self._sessions.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
        )
        self._uow.commit()
        return raw_token, self._actor_for(user)

    def logout(self, raw_token: str | None) -> None:
        """Delete the session for this cookie token."""
        if not raw_token:
            return
        self._sessions.delete_by_token_hash(hash_session_token(raw_token))
        self._uow.commit()

    def resolve_actor(self, raw_token: str | None) -> Actor | None:
        """Turn a cookie token into an Actor, or None if invalid/expired."""
        if not raw_token:
            return None
        found = self._sessions.get_by_token_hash(hash_session_token(raw_token))
        if found is None:
            return None
        _session_id, user_id, expires_at = found
        now = self._clock.now()
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=now.tzinfo)
        if expires_at <= now:
            self._sessions.delete_by_token_hash(hash_session_token(raw_token))
            self._uow.commit()
            return None
        user = self._users.get(user_id)
        if user is None or not user.is_active:
            return None
        return self._actor_for(user)

    def change_own_password(
        self,
        actor: Actor,
        *,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change password for the signed-in user and revoke all sessions."""
        user = self._require_user(actor.user_id)
        if not self._hasher.verify(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")
        _validate_password(new_password)
        user.change_password(self._hasher.hash(new_password), now=self._clock.now())
        self._users.save(user)
        self._sessions.delete_all_for_user(user.id)
        self._uow.collect(user.pull_events())
        self._uow.commit()

    def _actor_for(self, user: User) -> Actor:
        """Build the request Actor from a User and their role permissions."""
        is_superuser = self._roles.user_is_superuser(user.role_names)
        permissions = self._roles.permissions_for_roles(user.role_names)
        return Actor(
            user_id=user.id,
            email=user.email,
            roles=frozenset(user.role_names),
            permissions=frozenset(permissions),
            is_superuser=is_superuser,
        )

    def _require_user(self, user_id: UserId) -> User:
        """Load a user or treat as unauthenticated."""
        user = self._users.get(user_id)
        if user is None:
            raise UnauthorizedError()
        return user


def hash_session_token(raw_token: str) -> str:
    """Hash the cookie token for storage (never store the raw value)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _validate_password(password: str) -> None:
    """Enforce minimum password length (12+)."""
    if len(password) < 12:
        raise ValidationError(
            "Password must be at least 12 characters.",
            fields={"password": "Password must be at least 12 characters."},
        )
