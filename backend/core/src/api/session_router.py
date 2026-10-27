from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from config.settings import Settings
from application.auth_service import AuthService
from api.deps import get_auth_service, get_settings_from_app
from api.dto import LoginRequest, MeResponse

router = APIRouter(tags=["sessions"])


@router.post("/sessions", status_code=201)
def create_session(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> MeResponse:
    """Log in: set HttpOnly session cookie and return the actor profile."""
    client_key = request.client.host if request.client else "unknown"
    raw_token, actor = auth.login(
        email=str(body.email),
        password=body.password,
        client_key=client_key,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return MeResponse(
        id=str(actor.user_id),
        email=actor.email,
        is_active=True,
        roles=sorted(actor.roles),
        permissions=sorted(actor.permissions),
        is_superuser=actor.is_superuser,
    )


@router.delete("/sessions/current", status_code=204)
def delete_current_session(
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> Response:
    """Log out: revoke the current session and clear the cookie."""
    raw = request.cookies.get(settings.session_cookie_name)
    auth.logout(raw)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = 204
    return response
