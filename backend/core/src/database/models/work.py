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


class WorkflowRow(Base):
    """Named workflow graph for task types."""

    __tablename__ = "work_workflows"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowStatusRow(Base):
    """One status node in a workflow."""

    __tablename__ = "work_workflow_statuses"
    __table_args__ = (UniqueConstraint("workflow_id", "key"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    workflow_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_workflows.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WorkflowTransitionRow(Base):
    """One-way edge between statuses."""

    __tablename__ = "work_workflow_transitions"
    __table_args__ = (UniqueConstraint("workflow_id", "from_status_key", "to_status_key"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    workflow_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_workflows.id", ondelete="CASCADE"), nullable=False
    )
    from_status_key: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="")


class TaskTypeRow(Base):
    """Admin-defined task type bound to a workflow."""

    __tablename__ = "work_task_types"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workflow_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_workflows.id"), nullable=False
    )
    hierarchy_level: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskRow(Base):
    """Persisted work item."""

    __tablename__ = "work_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_type_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_task_types.id"), nullable=False
    )
    status_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    assignee_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    parent_task_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskStepRow(Base):
    """Checklist step on a task."""

    __tablename__ = "work_task_steps"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TaskCommentRow(Base):
    """Comment on a task."""

    __tablename__ = "work_task_comments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskAttachmentRow(Base):
    """Attachment metadata for a task."""

    __tablename__ = "work_task_attachments"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskEntityLinkRow(Base):
    """Soft entity reference on a task."""

    __tablename__ = "work_task_entity_links"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)


class TaskLinkRow(Base):
    """Peer link between two tasks."""

    __tablename__ = "work_task_links"
    __table_args__ = (UniqueConstraint("from_task_id", "to_task_id", "link_type"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    from_task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    to_task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("work_tasks.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(32), nullable=False)


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
