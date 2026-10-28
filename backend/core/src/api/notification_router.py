from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from api.deps import get_current_actor, get_db
from application.actor import Actor
from database.repositories.work_repository import SqlAlchemyWorkRepository
from domain.shared.domain_error import ForbiddenError, NotFoundError

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
def list_notifications(
    actor: Annotated[Actor, Depends(get_current_actor)],
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """List the caller's in-app notifications."""
    work = SqlAlchemyWorkRepository(session)
    rows, total = work.list_notifications(
        recipient_user_id=actor.user_id.value, page=page, page_size=page_size
    )
    return {
        "data": [
            {
                "id": str(r.id),
                "kind": r.kind,
                "title": r.title,
                "body": r.body,
                "taskId": str(r.task_id) if r.task_id else None,
                "taskUrl": r.task_url,
                "eventId": str(r.event_id),
                "readAt": r.read_at.isoformat() if r.read_at else None,
                "createdAt": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.get("/notifications/unread-count")
def unread_count(
    actor: Annotated[Actor, Depends(get_current_actor)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    """Unread count for the notification bell (UI later)."""
    work = SqlAlchemyWorkRepository(session)
    return {"count": work.unread_count(actor.user_id.value)}


@router.post("/notifications/{notification_id}/read", status_code=204)
def mark_read(
    notification_id: UUID,
    actor: Annotated[Actor, Depends(get_current_actor)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    """Mark one of the caller's notifications as read."""
    work = SqlAlchemyWorkRepository(session)
    row = work.get_notification(notification_id)
    if row is None:
        raise NotFoundError("Notification not found.")
    if row.recipient_user_id != actor.user_id.value:
        raise ForbiddenError()
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        session.commit()
    return Response(status_code=204)


@router.post("/notifications/read-all", status_code=204)
def mark_all_read(
    actor: Annotated[Actor, Depends(get_current_actor)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    """Mark all of the caller's notifications as read."""
    work = SqlAlchemyWorkRepository(session)
    rows, _ = work.list_notifications(
        recipient_user_id=actor.user_id.value, page=1, page_size=10_000
    )
    now = datetime.now(UTC)
    for row in rows:
        if row.read_at is None:
            row.read_at = now
    session.commit()
    return Response(status_code=204)
