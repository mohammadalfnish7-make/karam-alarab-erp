from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from api.deps import get_db, get_settings_from_app, get_uow, require_permission
from config.settings import Settings
from domain.shared.clock import SystemClock
from support.events import UnitOfWork
from notify.application.channel_service import ChannelService
from notify.database.repositories.notify_repository import SqlAlchemyNotifyRepository

__all__ = [
    "get_channel_service",
    "require_permission",
]


def get_channel_service(
    session: Annotated[Session, Depends(get_db)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> ChannelService:
    """Wire ChannelService for this request."""
    return ChannelService(
        work=SqlAlchemyNotifyRepository(session),
        clock=SystemClock(),
        uow=uow,
        settings=settings,
    )
