from __future__ import annotations

from application.actor import Actor
from application.auth_service import _validate_password
from domain.identity.ports import (
    PasswordHasher,
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from domain.identity.user import User
from domain.shared.clock import Clock
from domain.shared.domain_error import ConflictError, NotFoundError, ValidationError
from domain.shared.user_id import UserId
from support.events import UnitOfWork


class UserService:
    """Admin user CRUD, role grants, and permission registration."""

    def __init__(
        self,
        *,
        users: UserRepository,
        roles: RoleRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        """Wire user/role/session ports, hasher, clock, and UoW."""
        self._users = users
        self._roles = roles
        self._sessions = sessions
        self._hasher = hasher
        self._clock = clock
        self._uow = uow

    def create_user(
        self,
        *,
        email: str,
        password: str,
        roles: set[str],
    ) -> User:
        """Create a staff user with hashed password and assigned roles."""
        _validate_password(password)
        self._roles.ensure_roles_exist(roles)
        if self._users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists.")
        user = User.register(
            email=email,
            password_hash=self._hasher.hash(password),
            role_names=roles,
            now=self._clock.now(),
        )
        self._users.save(user)
        self._uow.collect(user.pull_events())
        self._uow.commit()
        return user

    def list_users(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        """Page through staff users."""
        return self._users.list_users(page=page, page_size=page_size)

    def get_user(self, actor: Actor, user_id: UserId) -> User:
        """Load a user; other users require identity_access:read (else 404)."""
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError()
        if actor.user_id != user_id and not actor.has_permission("identity_access:read"):
            raise NotFoundError()
        return user

    def update_user(
        self,
        user_id: UserId,
        *,
        roles: set[str] | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Change roles and/or active flag; revoke sessions on deactivate."""
        user = self._users.get(user_id)
        if user is None:
            raise NotFoundError()
        now = self._clock.now()
        if roles is not None:
            self._roles.ensure_roles_exist(roles)
            user.assign_roles(roles, now=now)
        if is_active is False:
            remaining = self._users.count_active_admins()
            user.deactivate(now=now, remaining_admins=remaining)
            self._sessions.delete_all_for_user(user.id)
        elif is_active is True:
            user.activate(now=now)
        self._users.save(user)
        self._uow.collect(user.pull_events())
        self._uow.commit()
        return user

    def list_roles(self) -> list[tuple[str, bool, list[str]]]:
        """List roles with superuser flag and granted permissions."""
        return self._roles.list_roles()

    def list_permissions(self) -> list[str]:
        """List all registered permission name strings."""
        return self._roles.list_permissions()

    def set_role_permissions(self, role_name: str, permissions: list[str]) -> None:
        """Replace which permissions a non-admin role holds."""
        if not self._roles.role_exists(role_name):
            raise NotFoundError("Role not found.")
        if self._roles.is_superuser_role(role_name):
            # Superuser flag stays; listed grants are optional extras.
            pass
        self._roles.set_role_permissions(role_name, permissions)
        self._uow.commit()

    def register_permissions(self, names: list[str]) -> list[str]:
        """Insert new permission names so later modules can grant them."""
        if not names:
            raise ValidationError(
                "At least one permission is required.",
                fields={"permissions": "At least one permission is required."},
            )
        created = self._roles.register_permissions(names)
        self._uow.commit()
        return created
