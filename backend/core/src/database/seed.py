from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.settings import Settings
from domain.identity.user import User
from database.models.identity import PermissionRow, RolePermissionRow, RoleRow
from database.password import Argon2PasswordHasher
from database.repositories.user_repository import SqlAlchemyUserRepository

SEED_ROLES: list[tuple[str, bool]] = [
    ("admin", True),
    ("sales", False),
    ("operations", False),
    ("warehouse", False),
    ("support", False),
]

SEED_PERMISSIONS = (
    "identity_access:read",
    "identity_access:update",
    "work:read",
    "work:create",
    "work:update",
    "work:transition",
    "work:attach",
    "work:admin",
    "process:read",
)

# Default grants per role (admin gets every permission separately as superuser + links).
SEED_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "operations": (
        "work:read",
        "work:create",
        "work:update",
        "work:transition",
        "work:attach",
        "process:read",
    ),
    "warehouse": (
        "work:read",
        "work:update",
        "work:transition",
        "work:attach",
        "process:read",
    ),
    "support": (
        "work:read",
        "process:read",
    ),
    "sales": (
        "work:read",
        "process:read",
    ),
}


def _ensure_role_permissions(session: Session, role_name: str, permission_names: tuple[str, ...]) -> None:
    """Idempotently grant the listed permissions to a role."""
    role = session.scalar(select(RoleRow).where(RoleRow.name == role_name))
    assert role is not None
    for perm_name in permission_names:
        perm = session.scalar(select(PermissionRow).where(PermissionRow.name == perm_name))
        assert perm is not None
        link = session.scalar(
            select(RolePermissionRow).where(
                RolePermissionRow.role_id == role.id,
                RolePermissionRow.permission_id == perm.id,
            )
        )
        if link is None:
            session.add(RolePermissionRow(role_id=role.id, permission_id=perm.id))


def _ensure_user(
    users: SqlAlchemyUserRepository,
    *,
    email: str,
    password: str,
    roles: set[str],
) -> None:
    """Create the user when missing; never overwrite an existing account."""
    if not email.strip() or len(password) < 12:
        return
    if users.get_by_email(email.strip().lower()) is not None:
        return
    hasher = Argon2PasswordHasher()
    user = User.register(
        email=email,
        password_hash=hasher.hash(password),
        role_names=roles,
        now=datetime.now(UTC),
    )
    users.save(user)


def seed_identity_access(session: Session, settings: Settings) -> None:
    """Ensure roles, core permissions, and seed users exist."""
    for name, is_superuser in SEED_ROLES:
        existing = session.scalar(select(RoleRow).where(RoleRow.name == name))
        if existing is None:
            session.add(RoleRow(name=name, is_superuser=is_superuser))
        else:
            existing.is_superuser = is_superuser
    session.flush()

    for perm_name in SEED_PERMISSIONS:
        if session.scalar(select(PermissionRow).where(PermissionRow.name == perm_name)) is None:
            session.add(PermissionRow(name=perm_name))
    session.flush()

    admin = session.scalar(select(RoleRow).where(RoleRow.name == "admin"))
    assert admin is not None
    for perm_name in SEED_PERMISSIONS:
        perm = session.scalar(select(PermissionRow).where(PermissionRow.name == perm_name))
        assert perm is not None
        link = session.scalar(
            select(RolePermissionRow).where(
                RolePermissionRow.role_id == admin.id,
                RolePermissionRow.permission_id == perm.id,
            )
        )
        if link is None:
            session.add(RolePermissionRow(role_id=admin.id, permission_id=perm.id))

    for role_name, perms in SEED_ROLE_PERMISSIONS.items():
        _ensure_role_permissions(session, role_name, perms)
    session.flush()

    users = SqlAlchemyUserRepository(session)
    _ensure_user(
        users,
        email=settings.seed_admin_email,
        password=settings.seed_admin_password,
        roles={"admin"},
    )
    _ensure_user(
        users,
        email=settings.seed_ops_email,
        password=settings.seed_ops_password,
        roles={"operations"},
    )
    session.commit()
