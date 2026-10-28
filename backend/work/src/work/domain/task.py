from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4

from domain.shared.domain_error import ConflictError, ValidationError
from domain.shared.domain_event import DomainEvent
from domain.shared.user_id import UserId
from work.domain.events import (
    TaskAssigned,
    TaskAttachmentAdded,
    TaskAttachmentRemoved,
    TaskCommented,
    TaskCreated,
    TaskDueDateChanged,
    TaskEntityLinked,
    TaskEntityUnlinked,
    TaskFollowerAdded,
    TaskPriorityChanged,
    TaskReminderRequested,
    TaskStatusChanged,
    TaskStepChanged,
)

ALLOWED_ENTITY_TYPES = frozenset(
    {"user", "shipment", "location", "stock_position", "stored_file"}
)
ALLOWED_TASK_LINK_TYPES = frozenset({"blocks", "relates", "duplicates"})
ALLOWED_PRIORITIES = frozenset({"none", "low", "normal", "high", "urgent"})
DEFAULT_PRIORITY = "normal"


def _entity_link_summary(
    verb: str, entity_type: str, entity_id: str, label: str | None
) -> str:
    """Human activity line; prefer a display label over raw ids."""
    cleaned = (label or "").strip()
    if entity_type == "stored_file":
        if cleaned:
            return f'{verb} file “{cleaned}”'
        return f"{verb} file {entity_id}"
    if cleaned:
        return f"{verb} {entity_type} “{cleaned}”"
    return f"{verb} {entity_type} {entity_id}"


@dataclass
class TaskStep:
    """Ordered checklist item on a task."""

    id: UUID
    title: str
    position: int
    is_done: bool = False


@dataclass
class TaskComment:
    """Comment authored on a task."""

    id: UUID
    author_user_id: UserId
    body: str
    created_at: datetime


@dataclass
class TaskAttachment:
    """File metadata attached to a task (bytes live in storage)."""

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    uploaded_by: UserId
    created_at: datetime


@dataclass
class EntityLink:
    """Soft link from a task to another ERP entity by type + id."""

    entity_type: str
    entity_id: str


@dataclass
class Task:
    """Work item aggregate: status transitions follow the type's workflow."""

    id: UUID
    task_type_id: UUID
    status_key: str
    title: str
    description: str
    assignee_user_id: UserId | None
    created_by: UserId
    created_at: datetime
    updated_at: datetime
    parent_task_id: UUID | None = None
    due_on: date | None = None
    priority: str = DEFAULT_PRIORITY
    # Human reference like "collecting payment-12" (frozen at create).
    reference: str = ""
    sequence_number: int = 0
    steps: list[TaskStep] = field(default_factory=list)
    comments: list[TaskComment] = field(default_factory=list)
    attachments: list[TaskAttachment] = field(default_factory=list)
    entity_links: list[EntityLink] = field(default_factory=list)
    follower_user_ids: list[UserId] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @staticmethod
    def create(
        *,
        task_type_id: UUID,
        initial_status_key: str,
        title: str,
        description: str,
        created_by: UserId,
        actor_email: str,
        now: datetime,
        reference: str,
        sequence_number: int,
        assignee_user_id: UserId | None = None,
        assignee_email: str = "",
        parent_task_id: UUID | None = None,
        due_on: date | None = None,
        priority: str = DEFAULT_PRIORITY,
    ) -> Task:
        """Open a new task in the workflow's initial status."""
        cleaned = title.strip()
        if not cleaned:
            raise ValidationError(
                "Title is required.",
                fields={"title": "Title is required."},
            )
        cleaned_ref = reference.strip()
        if not cleaned_ref:
            raise ValidationError(
                "Task reference is required.",
                fields={"reference": "Task reference is required."},
            )
        if sequence_number < 1:
            raise ValidationError(
                "Task sequence must be a positive number.",
                fields={"sequence_number": "Task sequence must be a positive number."},
            )
        cleaned_priority = _normalize_priority(priority)
        task_id = uuid4()
        task = Task(
            id=task_id,
            task_type_id=task_type_id,
            status_key=initial_status_key,
            title=cleaned,
            description=description or "",
            assignee_user_id=assignee_user_id,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            parent_task_id=parent_task_id,
            due_on=due_on,
            priority=cleaned_priority,
            reference=cleaned_ref,
            sequence_number=sequence_number,
        )
        task._events.append(
            TaskCreated(
                aggregate_id=str(task_id),
                task_id=str(task_id),
                task_type_id=str(task_type_id),
                title=cleaned,
                status_key=initial_status_key,
                created_by=str(created_by),
                actor_email=actor_email,
                priority=cleaned_priority,
                due_on=due_on.isoformat() if due_on else "",
                reference=cleaned_ref,
                occurred_at=now,
            )
        )
        if assignee_user_id is not None:
            task._events.append(
                TaskAssigned(
                    aggregate_id=str(task_id),
                    task_id=str(task_id),
                    title=cleaned,
                    task_type_id=str(task_type_id),
                    status_key=initial_status_key,
                    assignee_user_id=str(assignee_user_id),
                    assignee_email=assignee_email,
                    assigner_user_id=str(created_by),
                    assigner_email=actor_email,
                    occurred_at=now,
                )
            )
        return task

    def transition(
        self,
        *,
        to_status_key: str,
        allowed_targets: set[str],
        actor_user_id: UserId,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Move to another status if the workflow edge exists."""
        target = to_status_key.strip()
        if target not in allowed_targets:
            raise ConflictError(
                f"This task cannot move from “{self.status_key}” to “{target}”. "
                "Choose a status allowed by the workflow."
            )
        previous = self.status_key
        self.status_key = target
        self.updated_at = now
        self._events.append(
            TaskStatusChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                from_status_key=previous,
                to_status_key=target,
                actor_user_id=str(actor_user_id),
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def assign(
        self,
        *,
        assignee_user_id: UserId | None,
        assignee_email: str,
        assigner_user_id: UserId,
        assigner_email: str,
        now: datetime,
    ) -> None:
        """Set or clear assignee; emit TaskAssigned when set to a new user."""
        previous = self.assignee_user_id
        self.assignee_user_id = assignee_user_id
        self.updated_at = now
        if assignee_user_id is None:
            return
        if previous is not None and previous == assignee_user_id:
            return
        self._events.append(
            TaskAssigned(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                task_type_id=str(self.task_type_id),
                status_key=self.status_key,
                assignee_user_id=str(assignee_user_id),
                assignee_email=assignee_email,
                assigner_user_id=str(assigner_user_id),
                assigner_email=assigner_email,
                occurred_at=now,
            )
        )

    def set_due_on(
        self,
        *,
        due_on: date | None,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Set or clear the Dubai calendar due date."""
        if self.due_on == due_on:
            return
        self.due_on = due_on
        self.updated_at = now
        self._events.append(
            TaskDueDateChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                due_on=due_on.isoformat() if due_on else "",
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def set_priority(
        self,
        *,
        priority: str,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Change priority."""
        cleaned = _normalize_priority(priority)
        if self.priority == cleaned:
            return
        self.priority = cleaned
        self.updated_at = now
        self._events.append(
            TaskPriorityChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                priority=cleaned,
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def add_step(self, title: str, *, actor_email: str, now: datetime) -> TaskStep:
        """Append a checklist step."""
        cleaned = title.strip()
        if not cleaned:
            raise ValidationError(
                "Step title is required.",
                fields={"title": "Step title is required."},
            )
        step = TaskStep(
            id=uuid4(),
            title=cleaned,
            position=len(self.steps),
            is_done=False,
        )
        self.steps.append(step)
        self.updated_at = now
        self._events.append(
            TaskStepChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"Added step “{cleaned}”",
                actor_email=actor_email,
                occurred_at=now,
            )
        )
        return step

    def rename_step(
        self,
        step_id: UUID,
        *,
        title: str,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Change a checklist step title."""
        cleaned = title.strip()
        if not cleaned:
            raise ValidationError(
                "Step title is required.",
                fields={"title": "Step title is required."},
            )
        step = self._step_by_id(step_id)
        if step.title == cleaned:
            return
        previous = step.title
        step.title = cleaned
        self.updated_at = now
        self._events.append(
            TaskStepChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"Renamed step “{previous}” → “{cleaned}”",
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def delete_step(
        self,
        step_id: UUID,
        *,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Remove a checklist step and compact positions."""
        step = self._step_by_id(step_id)
        removed_title = step.title
        self.steps = [s for s in self.steps if s.id != step_id]
        for index, remaining in enumerate(self.steps):
            remaining.position = index
        self.updated_at = now
        self._events.append(
            TaskStepChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"Deleted step “{removed_title}”",
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def complete_step(
        self,
        step_id: UUID,
        *,
        is_done: bool = True,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Mark a step done or not done."""
        step = self._step_by_id(step_id)
        step.is_done = is_done
        self.updated_at = now
        verb = "Completed" if is_done else "Reopened"
        self._events.append(
            TaskStepChanged(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"{verb} step “{step.title}”",
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def _step_by_id(self, step_id: UUID) -> TaskStep:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise ValidationError(
            "Step not found.",
            fields={"step_id": "Step not found."},
        )

    def add_comment(
        self,
        *,
        author_user_id: UserId,
        actor_email: str,
        body: str,
        now: datetime,
    ) -> TaskComment:
        """Add a comment."""
        cleaned = body.strip()
        if not cleaned:
            raise ValidationError(
                "Comment body is required.",
                fields={"body": "Comment body is required."},
            )
        comment = TaskComment(
            id=uuid4(),
            author_user_id=author_user_id,
            body=cleaned,
            created_at=now,
        )
        self.comments.append(comment)
        self.updated_at = now
        preview = cleaned if len(cleaned) <= 80 else f"{cleaned[:77]}…"
        self._events.append(
            TaskCommented(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"Commented: {preview}",
                actor_email=actor_email,
                occurred_at=now,
            )
        )
        return comment

    def add_attachment(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        uploaded_by: UserId,
        actor_email: str,
        now: datetime,
        max_bytes: int,
        allowed_content_types: set[str],
    ) -> TaskAttachment:
        """Attach a file after size/MIME checks."""
        name = filename.strip()
        if not name:
            raise ValidationError(
                "Filename is required.",
                fields={"filename": "Filename is required."},
            )
        if size_bytes <= 0:
            raise ValidationError(
                "Empty files are not allowed.",
                fields={"file": "Empty files are not allowed."},
            )
        if size_bytes > max_bytes:
            raise ValidationError(
                "File is too large.",
                fields={"file": "File is too large."},
            )
        if content_type not in allowed_content_types:
            raise ValidationError(
                "File type is not allowed.",
                fields={"file": "File type is not allowed."},
            )
        attachment = TaskAttachment(
            id=uuid4(),
            filename=name,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            created_at=now,
        )
        self.attachments.append(attachment)
        self.updated_at = now
        self._events.append(
            TaskAttachmentAdded(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=f"Attached “{name}”",
                actor_email=actor_email,
                occurred_at=now,
            )
        )
        return attachment

    def add_entity_link(
        self,
        entity_type: str,
        entity_id: str,
        *,
        actor_email: str,
        now: datetime,
        label: str | None = None,
    ) -> EntityLink:
        """Link an ERP entity by allow-listed type."""
        et = entity_type.strip().lower()
        eid = entity_id.strip()
        if et not in ALLOWED_ENTITY_TYPES:
            allowed = ", ".join(sorted(ALLOWED_ENTITY_TYPES))
            raise ValidationError(
                f"Entity type must be one of: {allowed}.",
                fields={"entity_type": f"Use one of: {allowed}."},
            )
        if not eid:
            raise ValidationError(
                "Entity id is required.",
                fields={"entity_id": "Entity id is required."},
            )
        if any(l.entity_type == et and l.entity_id == eid for l in self.entity_links):
            raise ConflictError("This entity is already linked to the task.")
        link = EntityLink(entity_type=et, entity_id=eid)
        self.entity_links.append(link)
        self.updated_at = now
        self._events.append(
            TaskEntityLinked(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=_entity_link_summary("Linked", et, eid, label),
                actor_email=actor_email,
                occurred_at=now,
            )
        )
        return link

    def remove_entity_link(
        self,
        entity_type: str,
        entity_id: str,
        *,
        actor_email: str,
        now: datetime,
        label: str | None = None,
    ) -> None:
        """Remove a soft entity link from the task."""
        et = entity_type.strip().lower()
        eid = entity_id.strip()
        before = len(self.entity_links)
        self.entity_links = [
            link
            for link in self.entity_links
            if not (link.entity_type == et and link.entity_id == eid)
        ]
        if len(self.entity_links) == before:
            raise ValidationError(
                "Link not found.",
                fields={"entity_id": "Link not found."},
            )
        self.updated_at = now
        self._events.append(
            TaskEntityUnlinked(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                summary=_entity_link_summary("Unlinked", et, eid, label),
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def remove_attachment(
        self,
        attachment_id: UUID,
        *,
        actor_email: str,
        now: datetime,
    ) -> TaskAttachment:
        """Remove a direct attachment; caller deletes storage bytes."""
        for att in self.attachments:
            if att.id == attachment_id:
                self.attachments = [a for a in self.attachments if a.id != attachment_id]
                self.updated_at = now
                self._events.append(
                    TaskAttachmentRemoved(
                        aggregate_id=str(self.id),
                        task_id=str(self.id),
                        title=self.title,
                        summary=f"Removed attachment “{att.filename}”",
                        actor_email=actor_email,
                        occurred_at=now,
                    )
                )
                return att
        raise ValidationError(
            "Attachment not found.",
            fields={"attachment_id": "Attachment not found."},
        )

    def add_follower(
        self,
        *,
        follower_user_id: UserId,
        actor_email: str,
        now: datetime,
    ) -> None:
        """Add a watcher who can remind the assignee."""
        if self.assignee_user_id is not None and self.assignee_user_id == follower_user_id:
            raise ValidationError(
                "The assignee cannot also be a follower.",
                fields={"follower_user_id": "Pick someone other than the assignee."},
            )
        if any(existing == follower_user_id for existing in self.follower_user_ids):
            return
        self.follower_user_ids.append(follower_user_id)
        self.updated_at = now
        self._events.append(
            TaskFollowerAdded(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                follower_user_id=str(follower_user_id),
                actor_email=actor_email,
                occurred_at=now,
            )
        )

    def remove_follower(self, follower_user_id: UserId, *, now: datetime) -> None:
        """Remove a follower."""
        before = len(self.follower_user_ids)
        self.follower_user_ids = [
            uid for uid in self.follower_user_ids if uid != follower_user_id
        ]
        if len(self.follower_user_ids) == before:
            raise ValidationError(
                "Follower not found.",
                fields={"follower_user_id": "Follower not found."},
            )
        self.updated_at = now

    def request_reminder(
        self,
        *,
        follower_user_id: UserId,
        follower_email: str,
        assignee_email: str,
        message: str,
        now: datetime,
    ) -> None:
        """Follower reminds the assignee about this task."""
        if self.assignee_user_id is None:
            raise ConflictError("This task has no assignee to remind.")
        if not any(uid == follower_user_id for uid in self.follower_user_ids):
            raise ConflictError("Only a follower of this task can send a reminder.")
        cleaned = message.strip()
        self.updated_at = now
        self._events.append(
            TaskReminderRequested(
                aggregate_id=str(self.id),
                task_id=str(self.id),
                title=self.title,
                task_type_id=str(self.task_type_id),
                status_key=self.status_key,
                assignee_user_id=str(self.assignee_user_id),
                assignee_email=assignee_email,
                follower_user_id=str(follower_user_id),
                follower_email=follower_email,
                message=cleaned or "Please follow up on this task.",
                occurred_at=now,
            )
        )

    def pull_events(self) -> list[DomainEvent]:
        """Drain and return pending domain events."""
        events = list(self._events)
        self._events.clear()
        return events


def _normalize_priority(priority: str) -> str:
    cleaned = priority.strip().lower()
    if cleaned not in ALLOWED_PRIORITIES:
        allowed = ", ".join(sorted(ALLOWED_PRIORITIES))
        raise ValidationError(
            f"Priority must be one of: {allowed}.",
            fields={"priority": f"Use one of: {allowed}."},
        )
    return cleaned
