"""WorkManagement tables: workflows, tasks, channels, notifications, deliveries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_workflows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "work_workflow_statuses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_initial", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["work_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "key"),
    )
    op.create_table(
        "work_workflow_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("from_status_key", sa.String(length=64), nullable=False),
        sa.Column("to_status_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["work_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "from_status_key", "to_status_key"),
    )
    op.create_table(
        "work_task_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("hierarchy_level", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["work_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "work_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_type_id", sa.Uuid(), nullable=False),
        sa.Column("status_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("assignee_user_id", sa.Uuid(), nullable=True),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_type_id"], ["work_task_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for table, cols in [
        (
            "work_task_steps",
            [
                sa.Column("id", sa.Uuid(), nullable=False),
                sa.Column("task_id", sa.Uuid(), nullable=False),
                sa.Column("title", sa.String(length=500), nullable=False),
                sa.Column("position", sa.Integer(), nullable=False),
                sa.Column("is_done", sa.Boolean(), nullable=False),
            ],
        ),
        (
            "work_task_comments",
            [
                sa.Column("id", sa.Uuid(), nullable=False),
                sa.Column("task_id", sa.Uuid(), nullable=False),
                sa.Column("author_user_id", sa.Uuid(), nullable=False),
                sa.Column("body", sa.Text(), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            ],
        ),
        (
            "work_task_attachments",
            [
                sa.Column("id", sa.Uuid(), nullable=False),
                sa.Column("task_id", sa.Uuid(), nullable=False),
                sa.Column("filename", sa.String(length=255), nullable=False),
                sa.Column("content_type", sa.String(length=128), nullable=False),
                sa.Column("size_bytes", sa.Integer(), nullable=False),
                sa.Column("storage_key", sa.String(length=512), nullable=False),
                sa.Column("uploaded_by", sa.Uuid(), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            ],
        ),
        (
            "work_task_entity_links",
            [
                sa.Column("id", sa.Uuid(), nullable=False),
                sa.Column("task_id", sa.Uuid(), nullable=False),
                sa.Column("entity_type", sa.String(length=64), nullable=False),
                sa.Column("entity_id", sa.String(length=128), nullable=False),
            ],
        ),
    ]:
        op.create_table(
            table,
            *cols,
            sa.ForeignKeyConstraint(["task_id"], ["work_tasks.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_table(
        "work_task_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("from_task_id", sa.Uuid(), nullable=False),
        sa.Column("to_task_id", sa.Uuid(), nullable=False),
        sa.Column("link_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["from_task_id"], ["work_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_task_id"], ["work_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_task_id", "to_task_id", "link_type"),
    )
    op.create_table(
        "work_notification_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("webhook_url", sa.String(length=2048), nullable=False),
        sa.Column("webhook_secret", sa.String(length=255), nullable=False),
        sa.Column("previous_secret", sa.String(length=255), nullable=True),
        sa.Column("previous_secret_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("disabled_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "work_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("task_url", sa.String(length=1024), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_notifications_recipient_user_id", "work_notifications", ["recipient_user_id"])
    op.create_index("ix_work_notifications_event_id", "work_notifications", ["event_id"])
    op.create_table(
        "work_webhook_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["work_notification_channels.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "channel_id"),
    )
    op.create_index("ix_work_webhook_deliveries_event_id", "work_webhook_deliveries", ["event_id"])


def downgrade() -> None:
    op.drop_table("work_webhook_deliveries")
    op.drop_table("work_notifications")
    op.drop_table("work_notification_channels")
    op.drop_table("work_task_links")
    op.drop_table("work_task_entity_links")
    op.drop_table("work_task_attachments")
    op.drop_table("work_task_comments")
    op.drop_table("work_task_steps")
    op.drop_table("work_tasks")
    op.drop_table("work_task_types")
    op.drop_table("work_workflow_transitions")
    op.drop_table("work_workflow_statuses")
    op.drop_table("work_workflows")
