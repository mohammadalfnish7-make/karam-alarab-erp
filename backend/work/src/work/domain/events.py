from __future__ import annotations

from dataclasses import dataclass

from domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCreated(DomainEvent):
    """A task was registered in the open work engine."""

    task_id: str = ""
    task_type_id: str = ""
    title: str = ""
    status_key: str = ""
    created_by: str = ""
    actor_email: str = ""
    priority: str = ""
    due_on: str = ""
    reference: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskAssigned(DomainEvent):
    """A task was assigned or reassigned to an employee."""

    task_id: str = ""
    title: str = ""
    task_type_id: str = ""
    status_key: str = ""
    assignee_user_id: str = ""
    assignee_email: str = ""
    assigner_user_id: str = ""
    assigner_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskStatusChanged(DomainEvent):
    """A task moved to another workflow status."""

    task_id: str = ""
    title: str = ""
    from_status_key: str = ""
    to_status_key: str = ""
    actor_user_id: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskDueDateChanged(DomainEvent):
    """A task due date was set or cleared."""

    task_id: str = ""
    title: str = ""
    due_on: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskPriorityChanged(DomainEvent):
    """A task priority was changed."""

    task_id: str = ""
    title: str = ""
    priority: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskStepChanged(DomainEvent):
    """A checklist step was added or completed."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCommented(DomainEvent):
    """A comment was added on a task."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskAttachmentAdded(DomainEvent):
    """A file was attached to a task."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskAttachmentRemoved(DomainEvent):
    """A direct attachment was removed from a task."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEntityLinked(DomainEvent):
    """A soft entity link was added to a task."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskEntityUnlinked(DomainEvent):
    """A soft entity link was removed from a task."""

    task_id: str = ""
    title: str = ""
    summary: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskFollowerAdded(DomainEvent):
    """A follower was added to a task."""

    task_id: str = ""
    title: str = ""
    follower_user_id: str = ""
    actor_email: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskReminderRequested(DomainEvent):
    """A follower asked to remind the assignee."""

    task_id: str = ""
    title: str = ""
    task_type_id: str = ""
    status_key: str = ""
    assignee_user_id: str = ""
    assignee_email: str = ""
    follower_user_id: str = ""
    follower_email: str = ""
    message: str = ""
