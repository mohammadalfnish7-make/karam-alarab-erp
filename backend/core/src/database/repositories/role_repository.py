from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from domain.identity.permission import normalize_permission_name
from database.models.identity import PermissionRow, RolePermissionRow, RoleRow
from domain.shared.domain_error import NotFoundError, ValidationError


class SqlAlchemyRoleRepository:
    """Open RBAC persistence: roles, permissions, grants."""

    def __init__(self, session: Session) -> None:
        """Bind this adapter to the request DB session."""
        self._session = session

    def list_roles(self) -> list[tuple[str, bool, list[str]]]:
        """List roles with superuser flag and permission names."""
        roles = self._session.scalars(select(RoleRow).order_by(RoleRow.name)).all()
        result: list[tuple[str, bool, list[str]]] = []
        for role in roles:
            perms = sorted(rp.permission.name for rp in role.permissions)
            result.append((role.name, role.is_superuser, perms))
        return result

    def list_permissions(self) -> list[str]:
        """List every registered permission name."""
        rows = self._session.scalars(
            select(PermissionRow).order_by(PermissionRow.name)
        ).all()
        return [row.name for row in rows]

    def role_exists(self, name: str) -> bool:
        """True if the role name exists."""
        return (
            self._session.scalar(select(RoleRow.id).where(RoleRow.name == name))
            is not None
        )

    def ensure_roles_exist(self, names: set[str]) -> None:
        """Raise ValidationError if any role name is missing."""
        existing = {
            r.name
            for r in self._session.scalars(
                select(RoleRow).where(RoleRow.name.in_(names))
            ).all()
        }
        missing = names - existing
        if missing:
            raise ValidationError(
                f"Unknown role(s): {', '.join(sorted(missing))}.",
                fields={"roles": f"Unknown role(s): {', '.join(sorted(missing))}."},
            )

    def register_permissions(self, names: list[str]) -> list[str]:
        """Insert missing permission names; return newly created ones."""
        created: list[str] = []
        for raw in names:
            name = normalize_permission_name(raw)
            existing = self._session.scalar(
                select(PermissionRow).where(PermissionRow.name == name)
            )
            if existing is None:
                self._session.add(PermissionRow(name=name))
                created.append(name)
        self._session.flush()
        return created

    def set_role_permissions(self, role_name: str, permission_names: list[str]) -> None:
        """Replace the permission grants for one role."""
        role = self._session.scalar(select(RoleRow).where(RoleRow.name == role_name))
        if role is None:
            raise NotFoundError("Role not found.")
        if role.is_superuser:
            # Superuser ignores explicit grants; keep table empty or as-is.
            # Plan: cannot strip admin's superuser. Replacing grants is allowed but unused.
            pass
        normalized = [normalize_permission_name(n) for n in permission_names]
        self.register_permissions(normalized)
        perm_rows = {
            p.name: p
            for p in self._session.scalars(
                select(PermissionRow).where(PermissionRow.name.in_(normalized))
            ).all()
        }
        self._session.execute(
            delete(RolePermissionRow).where(RolePermissionRow.role_id == role.id)
        )
        for name in normalized:
            self._session.add(
                RolePermissionRow(role_id=role.id, permission_id=perm_rows[name].id)
            )
        self._session.flush()

    def permissions_for_roles(self, role_names: set[str]) -> set[str]:
        """Resolve effective permissions (all names if superuser)."""
        if not role_names:
            return set()
        if self.user_is_superuser(role_names):
            return set(self.list_permissions())
        rows = self._session.scalars(
            select(PermissionRow.name)
            .join(RolePermissionRow, RolePermissionRow.permission_id == PermissionRow.id)
            .join(RoleRow, RoleRow.id == RolePermissionRow.role_id)
            .where(RoleRow.name.in_(role_names))
        ).all()
        return set(rows)

    def is_superuser_role(self, role_name: str) -> bool:
        """True if this role bypasses explicit grants."""
        role = self._session.scalar(select(RoleRow).where(RoleRow.name == role_name))
        return bool(role and role.is_superuser)

    def user_is_superuser(self, role_names: set[str]) -> bool:
        """True if any assigned role is a superuser role."""
        if not role_names:
            return False
        return (
            self._session.scalar(
                select(RoleRow.id).where(
                    RoleRow.name.in_(role_names),
                    RoleRow.is_superuser.is_(True),
                )
            )
            is not None
        )
