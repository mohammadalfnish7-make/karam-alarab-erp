from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignNotifyCommand:
    """Notify-side command: deliver assign alert (no Work package dependency)."""

    event_id: UUID
    occurred_at: datetime
    task_id: str
    title: str
    task_type_id: str
    status_key: str
    assignee_user_id: str
    assignee_email: str
    assigner_user_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ReminderNotifyCommand:
    """Notify-side command: follower reminder to the assignee."""

    event_id: UUID
    occurred_at: datetime
    task_id: str
    title: str
    task_type_id: str
    status_key: str
    assignee_user_id: str
    assignee_email: str
    follower_user_id: str
    follower_email: str
    message: str
