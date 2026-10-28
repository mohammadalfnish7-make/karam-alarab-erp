from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.identity.user import User
from database.models.identity import RoleRow, UserRoleRow, UserRow
from domain.shared.user_id import UserId


class SqlAlchemyUserRepository:
    """Persist and load User aggregates."""

    def __init__(self, session: Session) -> None:
        """Bind this adapter to the request DB session."""
        self._session = session

    def get(self, user_id: UserId) -> User | None:
        """Load one user by id."""
        row = self._session.get(UserRow, user_id.value)
        return self._to_domain(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        """Load one user by email."""
        row = self._session.scalar(
            select(UserRow).where(UserRow.email == email.strip().lower())
        )
        return self._to_domain(row) if row else None

    def save(self, user: User) -> None:
        """Insert or update a user and replace role links."""
        row = self._session.get(UserRow, user.id.value)
        if row is None:
            row = UserRow(
                id=user.id.value,
                email=user.email,
                password_hash=user.password_hash,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            self._session.add(row)
        else:
            row.email = user.email
            row.password_hash = user.password_hash
            row.is_active = user.is_active
            row.updated_at = user.updated_at
            row.roles.clear()

        self._session.flush()
        role_rows = {
            r.name: r
            for r in self._session.scalars(
                select(RoleRow).where(RoleRow.name.in_(user.role_names))
            ).all()
        }
        missing = user.role_names - set(role_rows)
        if missing:
            raise ValueError(f"Roles not found: {', '.join(sorted(missing))}")
        for role in role_rows.values():
            self._session.add(UserRoleRow(user_id=user.id.value, role_id=role.id))
        self._session.flush()

    def list_users(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        """Return a page of users plus total count."""
        total = self._session.scalar(select(func.count()).select_from(UserRow)) or 0
        rows = self._session.scalars(
            select(UserRow)
            .order_by(UserRow.email)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [self._to_domain(row) for row in rows], int(total)

    def list_active_users(self) -> list[User]:
        """Return active users ordered by email (for task assignment)."""
        rows = self._session.scalars(
            select(UserRow)
            .where(UserRow.is_active.is_(True))
            .order_by(UserRow.email)
        ).all()
        return [self._to_domain(row) for row in rows]

    def count_active_admins(self) -> int:
        """Count active users that have the admin role."""
        stmt = (
            select(func.count(func.distinct(UserRow.id)))
            .select_from(UserRow)
            .join(UserRoleRow, UserRoleRow.user_id == UserRow.id)
            .join(RoleRow, RoleRow.id == UserRoleRow.role_id)
            .where(UserRow.is_active.is_(True), RoleRow.name == "admin")
        )
        return int(self._session.scalar(stmt) or 0)

    def _to_domain(self, row: UserRow) -> User:
        """Map a UserRow (with roles) to the User aggregate."""
        return User(
            id=UserId(row.id),
            email=row.email,
            password_hash=row.password_hash,
            is_active=row.is_active,
            role_names={ur.role.name for ur in row.roles},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
