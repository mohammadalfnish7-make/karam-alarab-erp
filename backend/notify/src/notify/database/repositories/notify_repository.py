from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from notify.database.models.notify import (
    NotificationChannelRow,
    NotificationRow,
    WebhookDeliveryRow,
)


class SqlAlchemyNotifyRepository:
    """Persist channels, inbox notifications, and webhook deliveries."""

    def __init__(self, session: Session) -> None:
        """Bind to the request DB session."""
        self._session = session

    def create_channel(
        self,
        *,
        name: str,
        webhook_url: str,
        webhook_secret: str,
        now: datetime,
    ) -> NotificationChannelRow:
        """Insert a notification channel."""
        row = NotificationChannelRow(
            id=uuid4(),
            name=name,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            previous_secret=None,
            previous_secret_expires_at=None,
            is_active=True,
            disabled_reason=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_channel(self, channel_id: UUID) -> NotificationChannelRow | None:
        """Load one channel."""
        return self._session.get(NotificationChannelRow, channel_id)

    def get_channel_by_name(self, name: str) -> NotificationChannelRow | None:
        """Load channel by unique name."""
        return self._session.scalar(
            select(NotificationChannelRow).where(NotificationChannelRow.name == name)
        )

    def list_channels(self) -> list[NotificationChannelRow]:
        """List all channels."""
        return list(
            self._session.scalars(
                select(NotificationChannelRow).order_by(NotificationChannelRow.name)
            ).all()
        )

    def list_active_channels(self) -> list[NotificationChannelRow]:
        """List active channels for fan-out."""
        return list(
            self._session.scalars(
                select(NotificationChannelRow).where(
                    NotificationChannelRow.is_active.is_(True)
                )
            ).all()
        )

    def save_channel(self, row: NotificationChannelRow) -> None:
        """Flush channel changes."""
        self._session.add(row)
        self._session.flush()

    def delete_channel(self, channel_id: UUID) -> None:
        """Hard-delete a channel."""
        row = self._session.get(NotificationChannelRow, channel_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def create_notification(
        self,
        *,
        recipient_user_id: UUID,
        kind: str,
        title: str,
        body: str,
        task_id: UUID | None,
        task_url: str,
        event_id: UUID,
        payload: dict,
        now: datetime,
    ) -> UUID:
        """Insert an in-app notification."""
        notification_id = uuid4()
        self._session.add(
            NotificationRow(
                id=notification_id,
                recipient_user_id=recipient_user_id,
                kind=kind,
                title=title,
                body=body,
                task_id=task_id,
                task_url=task_url,
                event_id=event_id,
                payload_json=json.dumps(payload),
                read_at=None,
                created_at=now,
            )
        )
        self._session.flush()
        return notification_id

    def list_notifications(
        self, *, recipient_user_id: UUID, page: int, page_size: int
    ) -> tuple[list[NotificationRow], int]:
        """Page a user's inbox."""
        total = int(
            self._session.scalar(
                select(func.count())
                .select_from(NotificationRow)
                .where(NotificationRow.recipient_user_id == recipient_user_id)
            )
            or 0
        )
        rows = self._session.scalars(
            select(NotificationRow)
            .where(NotificationRow.recipient_user_id == recipient_user_id)
            .order_by(NotificationRow.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def unread_count(self, recipient_user_id: UUID) -> int:
        """Count unread notifications for a user."""
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(NotificationRow)
                .where(
                    NotificationRow.recipient_user_id == recipient_user_id,
                    NotificationRow.read_at.is_(None),
                )
            )
            or 0
        )

    def get_notification(self, notification_id: UUID) -> NotificationRow | None:
        """Load one notification."""
        return self._session.get(NotificationRow, notification_id)

    def enqueue_delivery(
        self,
        *,
        event_id: UUID,
        channel_id: UUID,
        payload: dict,
        now: datetime,
    ) -> UUID:
        """Create a pending webhook delivery row."""
        delivery_id = uuid4()
        self._session.add(
            WebhookDeliveryRow(
                id=delivery_id,
                event_id=event_id,
                channel_id=channel_id,
                status="pending",
                attempts=0,
                next_attempt_at=now,
                last_error=None,
                payload_json=json.dumps(payload),
                created_at=now,
                updated_at=now,
            )
        )
        self._session.flush()
        return delivery_id

    def claim_due_deliveries(
        self, *, now: datetime, limit: int = 50
    ) -> list[WebhookDeliveryRow]:
        """Load pending/retryable deliveries that are due."""
        rows = self._session.scalars(
            select(WebhookDeliveryRow)
            .where(
                WebhookDeliveryRow.status.in_(("pending", "retry")),
                WebhookDeliveryRow.next_attempt_at <= now,
            )
            .order_by(WebhookDeliveryRow.next_attempt_at)
            .limit(limit)
        ).all()
        return list(rows)
