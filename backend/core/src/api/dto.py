from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ForbidModel(BaseModel):
    """Base request/response model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


class LoginRequest(ForbidModel):
    """Credentials for creating a session."""

    email: EmailStr
    password: str = Field(min_length=1)


class ChangePasswordRequest(ForbidModel):
    """Current and new password for self-service password change."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12)


class CreateUserRequest(ForbidModel):
    """Admin payload to register a new user with roles."""

    email: EmailStr
    password: str = Field(min_length=12)
    roles: list[str] = Field(min_length=1)


class UpdateUserRequest(ForbidModel):
    """Admin payload to change roles and/or active flag."""

    roles: list[str] | None = None
    is_active: bool | None = None


class SetRolePermissionsRequest(ForbidModel):
    """Replace the permission list granted to a role."""

    permissions: list[str]


class RegisterPermissionsRequest(ForbidModel):
    """Bootstrap payload to insert missing permission names."""

    permissions: list[str] = Field(min_length=1)


class UserResponse(ForbidModel):
    """Public user row for admin list/detail."""

    id: str
    email: str
    is_active: bool
    roles: list[str]


class MeResponse(ForbidModel):
    """Current session identity including effective permissions."""

    id: str
    email: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
    is_superuser: bool


class RoleResponse(ForbidModel):
    """One role with its grants and superuser flag."""

    name: str
    is_superuser: bool
    permissions: list[str]


class PageUsersResponse(ForbidModel):
    """Paginated user list envelope."""

    data: list[UserResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
