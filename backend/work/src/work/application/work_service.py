from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from uuid import UUID, uuid4

from application.actor import Actor
from database.repositories.user_repository import SqlAlchemyUserRepository
from domain.shared.clock import Clock
from domain.shared.domain_error import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from domain.shared.file_catalog import FileCatalog
from domain.shared.user_id import UserId
from support.events import UnitOfWork
from work.database.repositories.work_repository import SqlAlchemyWorkRepository
from work.domain.task import ALLOWED_TASK_LINK_TYPES, DEFAULT_PRIORITY, Task

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/json",
}


class WorkService:
    """Admin workflows/types and task use cases for WorkManagement."""

    def __init__(
        self,
        *,
        work: SqlAlchemyWorkRepository,
        users: SqlAlchemyUserRepository,
        clock: Clock,
        uow: UnitOfWork,
        upload_dir: Path,
        files: FileCatalog | None = None,
    ) -> None:
        """Wire work/user ports, clock, UoW, attachment directory, and file catalog."""
        self._work = work
        self._users = users
        self._clock = clock
        self._uow = uow
        self._upload_dir = upload_dir
        self._files = files

    def create_workflow(
        self,
        *,
        name: str,
        statuses: list[dict],
        transitions: list[dict],
    ) -> dict:
        """Admin: create a workflow with statuses and transitions."""
        cleaned = name.strip()
        if not cleaned:
            raise ValidationError(
                "Name is required.", fields={"name": "Name is required."}
            )
        if not statuses:
            raise ValidationError(
                "At least one status is required.",
                fields={"statuses": "At least one status is required."},
            )
        initials = [s for s in statuses if s.get("is_initial")]
        if len(initials) != 1:
            raise ValidationError(
                "Exactly one status must be initial.",
                fields={"statuses": "Exactly one status must be initial."},
            )
        keys = {s["key"] for s in statuses}
        for edge in transitions:
            if edge["from_status_key"] not in keys or edge["to_status_key"] not in keys:
                raise ValidationError(
                    "Transitions must reference known status keys.",
                    fields={"transitions": "Unknown status key in transition."},
                )
        now = self._clock.now()
        workflow_id = self._work.create_workflow(
            name=cleaned, statuses=statuses, transitions=transitions, now=now
        )
        self._uow.commit()
        result = self._work.get_workflow(workflow_id)
        assert result is not None
        return result

    def list_workflows(self) -> list[dict]:
        """List workflow summaries."""
        return self._work.list_workflows()

    def list_assignees(self) -> list[dict[str, str]]:
        """Active users that can be assigned a task (id + email)."""
        return [
            {"id": str(user.id.value), "email": user.email}
            for user in self._users.list_active_users()
        ]

    def get_workflow(self, workflow_id: UUID) -> dict:
        """Get one workflow graph."""
        row = self._work.get_workflow(workflow_id)
        if row is None:
            raise NotFoundError("Workflow not found.")
        return row

    def create_task_type(
        self,
        *,
        key: str,
        name: str,
        workflow_id: UUID,
        hierarchy_level: str = "standard",
    ) -> dict:
        """Admin: register an active task type bound to a workflow."""
        cleaned_key = key.strip().lower()
        if not _KEY_RE.match(cleaned_key):
            raise ValidationError(
                "Task type key must start with a letter and use lowercase letters, numbers, or underscores.",
                fields={
                    "key": (
                        "Use lowercase letters, numbers, and underscores only "
                        "(example: ops_check)."
                    )
                },
            )
        if hierarchy_level not in {"standard", "subtask"}:
            raise ValidationError(
                "Hierarchy level must be standard or subtask.",
                fields={"hierarchy_level": "Choose standard or subtask."},
            )
        if self._work.get_workflow(workflow_id) is None:
            raise NotFoundError("Workflow not found.")
        if self._work.get_task_type_by_key(cleaned_key) is not None:
            raise ConflictError("A task type with this key already exists.")
        now = self._clock.now()
        type_id = self._work.create_task_type(
            key=cleaned_key,
            name=name.strip() or cleaned_key,
            workflow_id=workflow_id,
            hierarchy_level=hierarchy_level,
            now=now,
        )
        self._uow.commit()
        row = self._work.get_task_type(type_id)
        assert row is not None
        return self._task_type_dict(row)

    def list_task_types(self, *, active_only: bool = False) -> list[dict]:
        """Fetch task types for admin or create forms."""
        return [
            self._task_type_dict(r)
            for r in self._work.list_task_types(active_only=active_only)
        ]

    def set_task_type_active(self, task_type_id: UUID, *, is_active: bool) -> dict:
        """Activate or deactivate a task type."""
        row = self._work.get_task_type(task_type_id)
        if row is None:
            raise NotFoundError("Task type not found.")
        self._work.set_task_type_active(task_type_id, is_active)
        self._uow.commit()
        row = self._work.get_task_type(task_type_id)
        assert row is not None
        return self._task_type_dict(row)

    def create_task(
        self,
        actor: Actor,
        *,
        task_type_id: UUID,
        title: str,
        description: str = "",
        assignee_user_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        due_on: date | None = None,
        priority: str = DEFAULT_PRIORITY,
        follower_user_ids: list[UUID] | None = None,
    ) -> Task:
        """Create a task from an active admin-defined type."""
        task_type = self._work.get_task_type(task_type_id)
        if task_type is None or not task_type.is_active:
            raise ValidationError(
                "Task type is missing or inactive.",
                fields={"task_type_id": "Task type is missing or inactive."},
            )
        initial = self._work.initial_status_key(task_type.workflow_id)
        if not initial:
            raise ConflictError(
                "This workflow has no starting status. Edit the workflow and mark one status as initial."
            )
        assignee = UserId(assignee_user_id) if assignee_user_id else None
        assignee_email = ""
        if assignee is not None:
            user = self._users.get(assignee)
            if user is None or not user.is_active:
                raise ValidationError(
                    "Assignee not found or inactive.",
                    fields={"assignee_user_id": "Assignee not found or inactive."},
                )
            assignee_email = user.email
        now = self._clock.now()
        sequence_number = self._work.allocate_task_sequence(task_type_id)
        reference = f"{task_type.name.strip()}-{sequence_number}"
        task = Task.create(
            task_type_id=task_type_id,
            initial_status_key=initial,
            title=title,
            description=description,
            created_by=actor.user_id,
            actor_email=actor.email,
            now=now,
            reference=reference,
            sequence_number=sequence_number,
            assignee_user_id=assignee,
            assignee_email=assignee_email,
            parent_task_id=parent_task_id,
            due_on=due_on,
            priority=priority,
        )
        for follower_id in follower_user_ids or []:
            follower = UserId(follower_id)
            user = self._users.get(follower)
            if user is None or not user.is_active:
                raise ValidationError(
                    "Follower not found or inactive.",
                    fields={"follower_user_ids": "Follower not found or inactive."},
                )
            task.add_follower(
                follower_user_id=follower,
                actor_email=actor.email,
                now=now,
            )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        loaded = self._work.get_task(task.id)
        assert loaded is not None
        return loaded

    def get_task(self, task_id: UUID) -> Task:
        """Load one task."""
        task = self._work.get_task(task_id)
        if task is None:
            raise NotFoundError("Task not found.")
        return task

    def list_tasks(
        self,
        *,
        page: int,
        page_size: int,
        assignee_user_id: UUID | None = None,
        status_key: str | None = None,
        task_type_id: UUID | None = None,
        priority: str | None = None,
        due_on_from: date | None = None,
        due_on_to: date | None = None,
        q: str | None = None,
    ) -> tuple[list[Task], int]:
        """Page tasks with filters."""
        return self._work.list_tasks(
            page=page,
            page_size=page_size,
            assignee_user_id=assignee_user_id,
            status_key=status_key,
            task_type_id=task_type_id,
            priority=priority,
            due_on_from=due_on_from,
            due_on_to=due_on_to,
            q=q,
        )

    def transition_task(self, actor: Actor, task_id: UUID, *, to_status_key: str) -> Task:
        """Apply a workflow transition."""
        task = self.get_task(task_id)
        task_type = self._work.get_task_type(task.task_type_id)
        assert task_type is not None
        targets = self._work.transition_targets(task_type.workflow_id, task.status_key)
        now = self._clock.now()
        task.transition(
            to_status_key=to_status_key,
            allowed_targets=targets,
            actor_user_id=actor.user_id,
            actor_email=actor.email,
            now=now,
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def assign_task(
        self,
        actor: Actor,
        task_id: UUID,
        *,
        assignee_user_id: UUID | None,
    ) -> Task:
        """Assign or unassign a task."""
        task = self.get_task(task_id)
        assignee = UserId(assignee_user_id) if assignee_user_id else None
        email = ""
        if assignee is not None:
            user = self._users.get(assignee)
            if user is None or not user.is_active:
                raise ValidationError(
                    "Assignee not found or inactive.",
                    fields={"assignee_user_id": "Assignee not found or inactive."},
                )
            email = user.email
        now = self._clock.now()
        task.assign(
            assignee_user_id=assignee,
            assignee_email=email,
            assigner_user_id=actor.user_id,
            assigner_email=actor.email,
            now=now,
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def patch_task(
        self,
        actor: Actor,
        task_id: UUID,
        *,
        due_on: date | None | object = ...,
        priority: str | None = None,
    ) -> Task:
        """Patch due date and/or priority on a task."""
        task = self.get_task(task_id)
        now = self._clock.now()
        if due_on is not ...:
            assert due_on is None or isinstance(due_on, date)
            task.set_due_on(due_on=due_on, actor_email=actor.email, now=now)
        if priority is not None:
            task.set_priority(priority=priority, actor_email=actor.email, now=now)
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def add_step(self, actor: Actor, task_id: UUID, *, title: str) -> Task:
        """Add a checklist step (task creator only)."""
        task = self.get_task(task_id)
        self._require_task_creator(actor, task)
        task.add_step(title, actor_email=actor.email, now=self._clock.now())
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def rename_step(
        self, actor: Actor, task_id: UUID, step_id: UUID, *, title: str
    ) -> Task:
        """Rename a checklist step (task creator only)."""
        task = self.get_task(task_id)
        self._require_task_creator(actor, task)
        task.rename_step(
            step_id,
            title=title,
            actor_email=actor.email,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def delete_step(self, actor: Actor, task_id: UUID, step_id: UUID) -> Task:
        """Delete a checklist step (task creator only)."""
        task = self.get_task(task_id)
        self._require_task_creator(actor, task)
        task.delete_step(
            step_id,
            actor_email=actor.email,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def complete_step(
        self, actor: Actor, task_id: UUID, step_id: UUID, *, is_done: bool
    ) -> Task:
        """Mark a step complete (any updater; usually the assignee)."""
        task = self.get_task(task_id)
        task.complete_step(
            step_id,
            is_done=is_done,
            actor_email=actor.email,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def _require_task_creator(self, actor: Actor, task: Task) -> None:
        """Creator or work admin may structure checklist steps."""
        if actor.user_id == task.created_by:
            return
        if "work:admin" in actor.permissions or actor.is_superuser:
            return
        raise ForbiddenError(
            "Only the person who created this task (or a work admin) "
            "can add, edit, or delete steps."
        )

    def add_comment(self, actor: Actor, task_id: UUID, *, body: str) -> Task:
        """Add a comment."""
        task = self.get_task(task_id)
        task.add_comment(
            author_user_id=actor.user_id,
            actor_email=actor.email,
            body=body,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def add_attachment(
        self,
        actor: Actor,
        task_id: UUID,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Task:
        """Store an attachment on disk and on the task."""
        task = self.get_task(task_id)
        storage_key = str(uuid4())
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        path = self._upload_dir / storage_key
        path.write_bytes(data)
        task.add_attachment(
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(data),
            storage_key=storage_key,
            uploaded_by=actor.user_id,
            actor_email=actor.email,
            now=self._clock.now(),
            max_bytes=MAX_ATTACHMENT_BYTES,
            allowed_content_types=ALLOWED_CONTENT_TYPES,
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def read_attachment_bytes(self, task_id: UUID, attachment_id: UUID) -> tuple[Task, bytes]:
        """Load attachment file bytes for download."""
        task = self.get_task(task_id)
        for att in task.attachments:
            if att.id == attachment_id:
                path = self._upload_dir / att.storage_key
                if not path.is_file():
                    raise NotFoundError("Attachment file missing.")
                return task, path.read_bytes()
        raise NotFoundError("Attachment not found.")

    def add_entity_link(
        self, actor: Actor, task_id: UUID, *, entity_type: str, entity_id: str
    ) -> Task:
        """Add a soft entity link."""
        task = self.get_task(task_id)
        task.add_entity_link(
            entity_type,
            entity_id,
            actor_email=actor.email,
            now=self._clock.now(),
            label=self._entity_label(entity_type, entity_id),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def remove_entity_link(
        self, actor: Actor, task_id: UUID, *, entity_type: str, entity_id: str
    ) -> Task:
        """Remove a soft entity link (does not delete the catalog file)."""
        task = self.get_task(task_id)
        task.remove_entity_link(
            entity_type,
            entity_id,
            actor_email=actor.email,
            now=self._clock.now(),
            label=self._entity_label(entity_type, entity_id),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def _entity_label(self, entity_type: str, entity_id: str) -> str | None:
        """Resolve a human label for activity (catalog display name for files)."""
        if entity_type.strip().lower() != "stored_file" or self._files is None:
            return None
        try:
            file_id = UUID(entity_id.strip())
        except ValueError:
            return None
        try:
            return self._files.get(file_id).display_name
        except NotFoundError:
            return None

    def remove_attachment(
        self, actor: Actor, task_id: UUID, attachment_id: UUID
    ) -> Task:
        """Remove a direct task attachment and delete its storage file."""
        task = self.get_task(task_id)
        removed = task.remove_attachment(
            attachment_id,
            actor_email=actor.email,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        path = self._upload_dir / removed.storage_key
        if path.is_file():
            path.unlink()
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def add_follower(self, actor: Actor, task_id: UUID, *, follower_user_id: UUID) -> Task:
        """Add a follower who can remind the assignee."""
        follower = UserId(follower_user_id)
        user = self._users.get(follower)
        if user is None or not user.is_active:
            raise ValidationError(
                "Follower not found or inactive.",
                fields={"follower_user_id": "Follower not found or inactive."},
            )
        task = self.get_task(task_id)
        task.add_follower(
            follower_user_id=follower,
            actor_email=actor.email,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def remove_follower(
        self, actor: Actor, task_id: UUID, *, follower_user_id: UUID
    ) -> Task:
        """Remove a follower."""
        _ = actor
        task = self.get_task(task_id)
        task.remove_follower(UserId(follower_user_id), now=self._clock.now())
        self._work.save_task(task)
        self._uow.commit()
        return self.get_task(task_id)

    def remind_assignee(
        self, actor: Actor, task_id: UUID, *, message: str = ""
    ) -> Task:
        """Follower sends a reminder notification to the assignee."""
        task = self.get_task(task_id)
        if task.assignee_user_id is None:
            raise ConflictError("This task has no assignee to remind.")
        assignee = self._users.get(task.assignee_user_id)
        assignee_email = assignee.email if assignee is not None else ""
        task.request_reminder(
            follower_user_id=actor.user_id,
            follower_email=actor.email,
            assignee_email=assignee_email,
            message=message,
            now=self._clock.now(),
        )
        self._work.save_task(task)
        self._uow.collect(task.pull_events())
        self._uow.commit()
        return self.get_task(task_id)

    def add_task_link(
        self, task_id: UUID, *, to_task_id: UUID, link_type: str
    ) -> list[dict]:
        """Link two tasks."""
        cleaned = link_type.strip().lower()
        if cleaned not in ALLOWED_TASK_LINK_TYPES:
            raise ValidationError(
                "Invalid link type.",
                fields={"link_type": "Invalid link type."},
            )
        if self._work.get_task(task_id) is None:
            raise NotFoundError("Task not found.")
        if self._work.get_task(to_task_id) is None:
            raise NotFoundError("Target task not found.")
        self._work.add_task_link(
            from_task_id=task_id, to_task_id=to_task_id, link_type=cleaned
        )
        self._uow.commit()
        return self._work.list_task_links(task_id)

    @staticmethod
    def _task_type_dict(row) -> dict:  # noqa: ANN001
        return {
            "id": row.id,
            "key": row.key,
            "name": row.name,
            "workflow_id": row.workflow_id,
            "hierarchy_level": row.hierarchy_level,
            "is_active": row.is_active,
        }


def require_work_permission(actor: Actor, permission: str) -> None:
    """Raise ForbiddenError when the actor lacks a work permission."""
    if not actor.has_permission(permission):
        raise ForbiddenError()
