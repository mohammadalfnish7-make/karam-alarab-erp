from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from domain.shared.domain_error import ConflictError, ValidationError
from domain.shared.domain_event import DomainEvent
from domain.shared.user_id import UserId
from work.domain.events import TaskAssigned, TaskCreated

ALLOWED_ENTITY_TYPES = frozenset(
    {"user", "shipment", "location", "stock_position"}
)
ALLOWED_TASK_LINK_TYPES = frozenset({"blocks", "relates", "duplicates"})


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
    steps: list[TaskStep] = field(default_factory=list)
    comments: list[TaskComment] = field(default_factory=list)
    attachments: list[TaskAttachment] = field(default_factory=list)
    entity_links: list[EntityLink] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @staticmethod
    def create(
        *,
        task_type_id: UUID,
        initial_status_key: str,
        title: str,
        description: str,
        created_by: UserId,
        now: datetime,
        assignee_user_id: UserId | None = None,
        assignee_email: str = "",
        parent_task_id: UUID | None = None,
    ) -> Task:
        """Open a new task in the workflow's initial status."""
        cleaned = title.strip()
        if not cleaned:
            raise ValidationError(
                "Title is required.",
                fields={"title": "Title is required."},
            )
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
        )
        task._events.append(
            TaskCreated(
                aggregate_id=str(task_id),
                task_id=str(task_id),
                task_type_id=str(task_type_id),
                title=cleaned,
                status_key=initial_status_key,
                created_by=str(created_by),
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
                    occurred_at=now,
                )
            )
        return task

    def transition(
        self,
        *,
        to_status_key: str,
        allowed_targets: set[str],
        now: datetime,
    ) -> None:
        """Move to another status if the workflow edge exists."""
        target = to_status_key.strip()
        if target not in allowed_targets:
            raise ConflictError(
                f"This task cannot move from “{self.status_key}” to “{target}”. "
                "Choose a status allowed by the workflow."
            )
        self.status_key = target
        self.updated_at = now

    def assign(
        self,
        *,
        assignee_user_id: UserId | None,
        assignee_email: str,
        assigner_user_id: UserId,
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
                occurred_at=now,
            )
        )

    def add_step(self, title: str) -> TaskStep:
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
        return step

    def complete_step(self, step_id: UUID, *, is_done: bool = True) -> None:
        """Mark a step done or not done."""
        for step in self.steps:
            if step.id == step_id:
                step.is_done = is_done
                return
        raise ValidationError(
            "Step not found.",
            fields={"step_id": "Step not found."},
        )

    def add_comment(
        self, *, author_user_id: UserId, body: str, now: datetime
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
        return comment

    def add_attachment(
        self,
        *,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        uploaded_by: UserId,
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
        return attachment

    def add_entity_link(self, entity_type: str, entity_id: str) -> EntityLink:
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
        link = EntityLink(entity_type=et, entity_id=eid)
        self.entity_links.append(link)
        return link

    def pull_events(self) -> list[DomainEvent]:
        """Drain and return pending domain events."""
        events = list(self._events)
        self._events.clear()
        return events
