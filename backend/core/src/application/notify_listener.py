from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from database.repositories.work_repository import SqlAlchemyWorkRepository
from domain.shared.domain_event import DomainEvent
from domain.work.events import TaskAssigned


class NotifyListener:
    """On TaskAssigned: write inbox Notification + per-channel delivery rows."""

    def __init__(self, session_factory: sessionmaker, settings: Settings) -> None:
        """Keep session factory and settings for deep links."""
        self._session_factory = session_factory
        self._settings = settings

    def handle(self, event: DomainEvent) -> None:
        """Enqueue in-app + webhook deliveries for TaskAssigned."""
        if not isinstance(event, TaskAssigned):
            return
        session = self._session_factory()
        try:
            work = SqlAlchemyWorkRepository(session)
            task_url = f"{self._settings.web_origin.rstrip('/')}/tasks/{event.task_id}"
            payload_base = {
                "event": "task_assigned",
                "event_id": str(event.event_id),
                "task_id": event.task_id,
                "title": event.title,
                "task_type_id": event.task_type_id,
                "status": event.status_key,
                "assignee_user_id": event.assignee_user_id,
                "assignee_email": event.assignee_email,
                "assigner_user_id": event.assigner_user_id,
                "task_url": task_url,
                "occurred_at": event.occurred_at.isoformat(),
            }
            work.create_notification(
                recipient_user_id=UUID(event.assignee_user_id),
                kind="task_assigned",
                title=f"Assigned: {event.title}",
                body=f"You were assigned task {event.task_id}",
                task_id=UUID(event.task_id),
                task_url=task_url,
                event_id=event.event_id,
                payload=payload_base,
                now=event.occurred_at,
            )
            for channel in work.list_active_channels():
                payload = {
                    **payload_base,
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                }
                work.enqueue_delivery(
                    event_id=event.event_id,
                    channel_id=channel.id,
                    payload=payload,
                    now=event.occurred_at,
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
