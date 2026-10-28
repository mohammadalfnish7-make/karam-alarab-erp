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
)


def seed_identity_access(session: Session, settings: Settings) -> None:
    """Ensure roles, core permissions, and the seed admin user exist."""
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
    session.flush()

    users = SqlAlchemyUserRepository(session)
    if users.get_by_email(settings.seed_admin_email.strip().lower()) is None:
        hasher = Argon2PasswordHasher()
        now = datetime.now(UTC)
        admin_user = User.register(
            email=settings.seed_admin_email,
            password_hash=hasher.hash(settings.seed_admin_password),
            role_names={"admin"},
            now=now,
        )
        users.save(admin_user)
    session.commit()
