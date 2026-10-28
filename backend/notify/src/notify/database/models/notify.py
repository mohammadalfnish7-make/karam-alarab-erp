from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from database.engine import Base


class NotificationChannelRow(Base):
    """Admin-managed outbound notify channel (name + webhook)."""

    __tablename__ = "work_notification_channels"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_secret_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationRow(Base):
    """In-app notification for an employee."""

    __tablename__ = "work_notifications"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    recipient_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    task_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    task_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WebhookDeliveryRow(Base):
    """Per-channel durable delivery of a notify event."""

    __tablename__ = "work_webhook_deliveries"
    __table_args__ = (UniqueConstraint("event_id", "channel_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_notification_channels.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
