from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from application.actor import Actor
from application.auth_service import AuthService
from application.user_service import UserService
from domain.identity.user import User
from api.deps import (
    get_auth_service,
    get_current_actor,
    get_user_service,
    require_permission,
)
from api.dto import (
    ChangePasswordRequest,
    CreateUserRequest,
    MeResponse,
    PageUsersResponse,
    RegisterPermissionsRequest,
    RoleResponse,
    SetRolePermissionsRequest,
    UpdateUserRequest,
    UserResponse,
)
from domain.shared.domain_error import ValidationError
from domain.shared.user_id import UserId

router = APIRouter(tags=["users"])


def _user_response(user: User) -> UserResponse:
    """Map a User aggregate to the admin UserResponse DTO."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        roles=sorted(user.role_names),
    )


@router.get("/users/me", response_model=MeResponse)
def get_me(actor: Annotated[Actor, Depends(get_current_actor)]) -> MeResponse:
    """Return the logged-in user's identity and effective permissions."""
    return MeResponse(
        id=str(actor.user_id),
        email=actor.email,
        is_active=True,
        roles=sorted(actor.roles),
        permissions=sorted(actor.permissions),
        is_superuser=actor.is_superuser,
    )


@router.patch("/users/me/password", status_code=204)
def change_my_password(
    body: ChangePasswordRequest,
    actor: Annotated[Actor, Depends(get_current_actor)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    """Let the caller change their own password (revokes other sessions)."""
    auth.change_own_password(
        actor,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return Response(status_code=204)


@router.get("/users", response_model=PageUsersResponse)
def list_users(
    _: Annotated[Actor, Depends(require_permission("identity_access:read"))],
    users: Annotated[UserService, Depends(get_user_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> PageUsersResponse:
    """Admin: list users with pagination."""
    items, total = users.list_users(page=page, page_size=page_size)
    return PageUsersResponse(
        data=[_user_response(u) for u in items],
        page=page,
        pageSize=page_size,
        total=total,
    )


@router.post("/users", status_code=201, response_model=UserResponse)
def create_user(
    body: CreateUserRequest,
    _: Annotated[Actor, Depends(require_permission("identity_access:update"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Admin: create a user with initial roles."""
    user = users.create_user(
        email=str(body.email),
        password=body.password,
        roles=set(body.roles),
    )
    return _user_response(user)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    actor: Annotated[Actor, Depends(get_current_actor)],
    users: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Fetch one user by id (self or identity_access:read)."""
    try:
        uid = UserId.from_string(user_id)
    except ValueError as exc:
        raise ValidationError(
            "User id must be a UUID.",
            fields={"user_id": "User id must be a UUID."},
        ) from exc
    return _user_response(users.get_user(actor, uid))


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _: Annotated[Actor, Depends(require_permission("identity_access:update"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Admin: update a user's roles and/or active status."""
    try:
        uid = UserId.from_string(user_id)
    except ValueError as exc:
        raise ValidationError(
            "User id must be a UUID.",
            fields={"user_id": "User id must be a UUID."},
        ) from exc
    if body.roles is None and body.is_active is None:
        raise ValidationError(
            "Provide roles and/or is_active.",
            fields={"body": "Provide roles and/or is_active."},
        )
    user = users.update_user(
        uid,
        roles=set(body.roles) if body.roles is not None else None,
        is_active=body.is_active,
    )
    return _user_response(user)


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    _: Annotated[Actor, Depends(require_permission("identity_access:read"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> list[RoleResponse]:
    """Admin: list roles with their permission grants."""
    return [
        RoleResponse(name=name, is_superuser=is_super, permissions=perms)
        for name, is_super, perms in users.list_roles()
    ]


@router.put("/roles/{role_name}/permissions", status_code=204)
def set_role_permissions(
    role_name: str,
    body: SetRolePermissionsRequest,
    _: Annotated[Actor, Depends(require_permission("identity_access:update"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> Response:
    """Admin: replace the permissions granted to one role."""
    users.set_role_permissions(role_name, body.permissions)
    return Response(status_code=204)


@router.get("/permissions", response_model=list[str])
def list_permissions(
    _: Annotated[Actor, Depends(require_permission("identity_access:read"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> list[str]:
    """Admin: list every registered permission name."""
    return users.list_permissions()


@router.post("/permissions/register", status_code=201, response_model=list[str])
def register_permissions(
    body: RegisterPermissionsRequest,
    _: Annotated[Actor, Depends(require_permission("identity_access:update"))],
    users: Annotated[UserService, Depends(get_user_service)],
) -> list[str]:
    """Admin helper / module bootstrap: insert missing permission names."""
    return users.register_permissions(body.permissions)
