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
