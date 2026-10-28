from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from notify.application.commands import AssignNotifyCommand, ReminderNotifyCommand
from notify.database.repositories.notify_repository import SqlAlchemyNotifyRepository
from support.tracing import TraceRecorder


class NotifyListener:
    """Enqueue inbox + webhook deliveries for work notify commands."""

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

    def handle_assign(self, command: AssignNotifyCommand) -> None:
        """Enqueue in-app + webhook deliveries for a task assignment."""
        self._enqueue(
            operation="task_assign_notify",
            correlation_id=str(command.event_id),
            task_id=command.task_id,
            event_id=command.event_id,
            occurred_at=command.occurred_at,
            kind="task_assigned",
            inbox_title=f"Assigned: {command.title}",
            inbox_body=f"You were assigned task {command.task_id}",
            recipient_user_id=command.assignee_user_id,
            payload_base={
                "event": "task_assigned",
                "event_id": str(command.event_id),
                "task_id": command.task_id,
                "title": command.title,
                "task_type_id": command.task_type_id,
                "status": command.status_key,
                "assignee_user_id": command.assignee_user_id,
                "assignee_email": command.assignee_email,
                "assigner_user_id": command.assigner_user_id,
                "occurred_at": command.occurred_at.isoformat(),
            },
            fail_summary="Assign notify failed while enqueueing.",
            success_label="Assign notify",
        )

    def handle_reminder(self, command: ReminderNotifyCommand) -> None:
        """Enqueue in-app + webhook deliveries for a follower reminder."""
        self._enqueue(
            operation="task_reminder_notify",
            correlation_id=str(command.event_id),
            task_id=command.task_id,
            event_id=command.event_id,
            occurred_at=command.occurred_at,
            kind="task_reminder",
            inbox_title=f"Reminder: {command.title}",
            inbox_body=f"{command.follower_email}: {command.message}",
            recipient_user_id=command.assignee_user_id,
            payload_base={
                "event": "task_reminder",
                "event_id": str(command.event_id),
                "task_id": command.task_id,
                "title": command.title,
                "task_type_id": command.task_type_id,
                "status": command.status_key,
                "assignee_user_id": command.assignee_user_id,
                "assignee_email": command.assignee_email,
                "follower_user_id": command.follower_user_id,
                "follower_email": command.follower_email,
                "message": command.message,
                "occurred_at": command.occurred_at.isoformat(),
            },
            fail_summary="Reminder notify failed while enqueueing.",
            success_label="Reminder notify",
        )

    def _enqueue(
        self,
        *,
        operation: str,
        correlation_id: str,
        task_id: str,
        event_id: UUID,
        occurred_at: datetime,
        kind: str,
        inbox_title: str,
        inbox_body: str,
        recipient_user_id: str,
        payload_base: dict[str, Any],
        fail_summary: str,
        success_label: str,
    ) -> None:
        """Shared inbox + webhook enqueue path."""
        trace_id = self._traces.start(
            context="work",
            operation=operation,
            correlation_id=correlation_id,
            entity_type="task",
            entity_id=task_id,
            summary=f"{success_label} for task {task_id}.",
        )
        pending_steps: list[dict[str, Any]] = []
        channel_count = 0
        failure: BaseException | None = None
        session = self._session_factory()
        try:
            repo = SqlAlchemyNotifyRepository(session)
            task_url = f"{self._settings.web_origin.rstrip('/')}/tasks/{task_id}"
            payload_base = {**payload_base, "task_url": task_url}
            repo.create_notification(
                recipient_user_id=UUID(recipient_user_id),
                kind=kind,
                title=inbox_title,
                body=inbox_body,
                task_id=UUID(task_id),
                task_url=task_url,
                event_id=event_id,
                payload=payload_base,
                now=occurred_at,
            )
            pending_steps.append(
                {
                    "step_key": "enqueue_inbox",
                    "status": "succeeded",
                    "summary": "Wrote in-app notification for recipient.",
                    "detail": {"recipientUserId": recipient_user_id},
                }
            )
            channels = repo.list_active_channels()
            channel_count = len(channels)
            for channel in channels:
                payload = {
                    **payload_base,
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                }
                delivery_id = repo.enqueue_delivery(
                    event_id=event_id,
                    channel_id=channel.id,
                    payload=payload,
                    now=occurred_at,
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
                summary=fail_summary,
                detail={"errorType": type(failure).__name__},
            )
            self._traces.fail(
                trace_id,
                summary=fail_summary,
                error_message=f"{type(failure).__name__}: {failure}",
            )
            raise failure

        self._traces.succeed(
            trace_id,
            summary=(
                f"{success_label} enqueued inbox"
                f"{f' and {channel_count} channel(s)' if channel_count else ''}."
            ),
        )
