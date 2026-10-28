from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from application.actor import Actor
from application.auth_service import AuthService
from application.user_service import UserService
from config.settings import Settings
from database.password import Argon2PasswordHasher
from database.repositories.login_attempts import SqlAlchemyLoginAttemptStore
from database.repositories.role_repository import SqlAlchemyRoleRepository
from database.repositories.session_repository import (
    SqlAlchemySessionRepository,
)
from database.repositories.user_repository import SqlAlchemyUserRepository
from domain.shared.clock import SystemClock
from domain.shared.domain_error import ForbiddenError, UnauthorizedError
from domain.shared.file_catalog import FileCatalog
from support.events import EventBus, UnitOfWork


def get_settings_from_app(request: Request) -> Settings:
    """Read runtime Settings from FastAPI app state."""
    return request.app.state.settings


def get_db(request: Request):
    """Open one SQLAlchemy session per request and close it after."""
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_event_bus(request: Request) -> EventBus:
    """Read the shared in-process EventBus from app state."""
    return request.app.state.event_bus


def get_uow(
    session: Annotated[Session, Depends(get_db)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> UnitOfWork:
    """Build a UnitOfWork that commits DB work and publishes events."""
    return UnitOfWork(session, event_bus)


def get_auth_service(
    session: Annotated[Session, Depends(get_db)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> AuthService:
    """Wire AuthService with SQLAlchemy adapters for this request."""
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        roles=SqlAlchemyRoleRepository(session),
        attempts=SqlAlchemyLoginAttemptStore(session),
        hasher=Argon2PasswordHasher(),
        clock=SystemClock(),
        uow=uow,
        session_ttl_seconds=settings.session_ttl_seconds,
    )


def get_user_service(
    session: Annotated[Session, Depends(get_db)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserService:
    """Wire UserService with SQLAlchemy adapters for this request."""
    return UserService(
        users=SqlAlchemyUserRepository(session),
        roles=SqlAlchemyRoleRepository(session),
        sessions=SqlAlchemySessionRepository(session),
        hasher=Argon2PasswordHasher(),
        clock=SystemClock(),
        uow=uow,
    )


def get_optional_actor(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> Actor | None:
    """Resolve the caller from the session cookie, or None if absent/invalid."""
    raw = request.cookies.get(settings.session_cookie_name)
    return auth.resolve_actor(raw)


def get_current_actor(
    actor: Annotated[Actor | None, Depends(get_optional_actor)],
) -> Actor:
    """Require a logged-in actor; raise 401 if no valid session."""
    if actor is None:
        raise UnauthorizedError()
    return actor


def get_file_catalog(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> FileCatalog:
    """Build the file catalog for this request. main.py supplies the factory."""
    upload_dir = Path(getattr(request.app.state, "upload_dir", settings.upload_dir))
    factory = request.app.state.file_catalog_factory
    return factory(session=session, uow=uow, upload_dir=upload_dir)


def require_permission(permission: str) -> Callable[..., Actor]:
    """FastAPI dependency factory: require login plus one permission name."""

    def _dependency(actor: Annotated[Actor, Depends(get_current_actor)]) -> Actor:
        """Reject the request unless the actor has the required permission."""
        if not actor.has_permission(permission):
            raise ForbiddenError()
        return actor

    return _dependency
