from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from api.deps import get_db, get_settings_from_app, get_uow, require_permission
from config.settings import Settings
from database.repositories.user_repository import SqlAlchemyUserRepository
from domain.shared.clock import SystemClock
from support.events import UnitOfWork
from work.application.work_service import WorkService
from work.database.repositories.work_repository import SqlAlchemyWorkRepository

__all__ = [
    "get_work_service",
    "require_permission",
]


def get_work_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> WorkService:
    """Wire WorkService for this request."""
    upload_dir = Path(getattr(request.app.state, "upload_dir", settings.upload_dir))
    return WorkService(
        work=SqlAlchemyWorkRepository(session),
        users=SqlAlchemyUserRepository(session),
        clock=SystemClock(),
        uow=uow,
        upload_dir=upload_dir,
    )
