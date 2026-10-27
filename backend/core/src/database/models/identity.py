from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class UserRow(Base):
    """Staff user credentials and active flag."""

    __tablename__ = "identity_access_users"

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    roles: Mapped[list[UserRoleRow]] = relationship(
        "UserRoleRow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RoleRow(Base):
    """Named role; admin has is_superuser=True."""

    __tablename__ = "identity_access_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions: Mapped[list[RolePermissionRow]] = relationship(
        "RolePermissionRow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PermissionRow(Base):
    """Permission name string, e.g. identity_access:read."""

    __tablename__ = "identity_access_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)


class RolePermissionRow(Base):
    """Which permissions a role is granted."""

    __tablename__ = "identity_access_role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("identity_access_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("identity_access_permissions.id", ondelete="CASCADE"),
        nullable=False,
    )

    permission: Mapped[PermissionRow] = relationship("PermissionRow", lazy="joined")


class UserRoleRow(Base):
    """Which roles a user holds."""

    __tablename__ = "identity_access_user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("identity_access_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("identity_access_roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[RoleRow] = relationship("RoleRow", lazy="joined")


class SessionRow(Base):
    """Server-side session; stores hashed cookie token."""

    __tablename__ = "identity_access_sessions"

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[object] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("identity_access_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LoginAttemptRow(Base):
    """Failed login attempt used for rate limiting."""

    __tablename__ = "identity_access_login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_key: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
