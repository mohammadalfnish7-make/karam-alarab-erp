from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from database.repositories.work_repository import SqlAlchemyWorkRepository
from domain.shared.domain_event import DomainEvent
from domain.work.events import TaskAssigned
from support.tracing import TraceRecorder


class NotifyListener:
    """On TaskAssigned: write inbox + deliveries and record ProcessTrace steps."""

    def __init__(
        self,
        session_factory: sessionmaker,
        settings: Settings,
        trace_recorder: TraceRecorder,
    ) -> None:
        """Keep session factory, settings, and core TraceRecorder."""
        self._session_factory = session_factory
        self._settings = settings
        self._traces = trace_recorder

    def handle(self, event: DomainEvent) -> None:
        """Enqueue in-app + webhook deliveries for TaskAssigned."""
        if not isinstance(event, TaskAssigned):
            return
        correlation_id = str(event.event_id)
        # Header commits in its own short session before business UoW.
        trace_id = self._traces.start(
            context="work",
            operation="task_assign_notify",
            correlation_id=correlation_id,
            entity_type="task",
            entity_id=event.task_id,
            summary=f"Assign notify for task {event.task_id}.",
        )
        # Stage steps are buffered so we do not open a second SQLite writer
        # while the business session still holds its transaction.
        pending_steps: list[dict[str, Any]] = []
        channel_count = 0
        failure: BaseException | None = None
        session = self._session_factory()
        try:
            work = SqlAlchemyWorkRepository(session)
            task_url = f"{self._settings.web_origin.rstrip('/')}/tasks/{event.task_id}"
            payload_base = {
                "event": "task_assigned",
                "event_id": correlation_id,
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
            pending_steps.append(
                {
                    "step_key": "enqueue_inbox",
                    "status": "succeeded",
                    "summary": "Wrote in-app notification for assignee.",
                    "detail": {"assigneeUserId": event.assignee_user_id},
                }
            )
            channels = work.list_active_channels()
            channel_count = len(channels)
            for channel in channels:
                payload = {
                    **payload_base,
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                }
                delivery_id = work.enqueue_delivery(
                    event_id=event.event_id,
                    channel_id=channel.id,
                    payload=payload,
                    now=event.occurred_at,
                )
                pending_steps.append(
                    {
                        "step_key": "enqueue_delivery",
                        "status": "succeeded",
                        "summary": f"Queued webhook delivery for channel “{channel.name}”.",
                        "detail": {
                            "channelId": str(channel.id),
                            "channelName": channel.name,
                            "deliveryId": str(delivery_id),
                        },
                    }
                )
            session.commit()
        except BaseException as exc:
            session.rollback()
            failure = exc
        finally:
            session.close()

        for step in pending_steps:
            self._traces.step(
                trace_id,
                step_key=step["step_key"],
                status=step["status"],
                summary=step["summary"],
                detail=step.get("detail"),
            )

        if failure is not None:
            self._traces.step(
                trace_id,
                step_key="enqueue_failed",
                status="failed",
                summary="Could not enqueue assign notifications.",
                detail={"errorType": type(failure).__name__},
            )
            self._traces.fail(
                trace_id,
                summary="Assign notify failed while enqueueing.",
                error_message=f"{type(failure).__name__}: {failure}",
            )
            raise failure

        self._traces.succeed(
            trace_id,
            summary=(
                "Assign notify enqueued inbox"
                f"{f' and {channel_count} channel(s)' if channel_count else ''}."
            ),
        )
