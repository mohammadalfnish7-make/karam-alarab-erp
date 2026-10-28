from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from work.database.models.work import (
    TaskAttachmentRow,
    TaskCommentRow,
    TaskEntityLinkRow,
    TaskFollowerRow,
    TaskLinkRow,
    TaskRow,
    TaskStepRow,
    TaskTypeRow,
    TaskTypeSequenceRow,
    WorkflowRow,
    WorkflowStatusRow,
    WorkflowTransitionRow,
)
from domain.shared.user_id import UserId
from work.domain.task import (
    EntityLink,
    Task,
    TaskAttachment,
    TaskComment,
    TaskStep,
)


class SqlAlchemyWorkRepository:
    """Persist workflows, task types, and tasks."""

    def __init__(self, session: Session) -> None:
        """Bind to the request DB session."""
        self._session = session

    # --- workflows / types ---

    def create_workflow(
        self,
        *,
        name: str,
        statuses: list[dict],
        transitions: list[dict],
        now: datetime,
    ) -> UUID:
        """Insert a workflow graph; return its id."""
        workflow_id = uuid4()
        self._session.add(WorkflowRow(id=workflow_id, name=name, created_at=now))
        for i, status in enumerate(statuses):
            self._session.add(
                WorkflowStatusRow(
                    id=uuid4(),
                    workflow_id=workflow_id,
                    key=status["key"],
                    name=status["name"],
                    is_initial=bool(status.get("is_initial", False)),
                    position=i,
                )
            )
        for edge in transitions:
            self._session.add(
                WorkflowTransitionRow(
                    id=uuid4(),
                    workflow_id=workflow_id,
                    from_status_key=edge["from_status_key"],
                    to_status_key=edge["to_status_key"],
                    name=edge.get("name", ""),
                )
            )
        self._session.flush()
        return workflow_id

    def get_workflow(self, workflow_id: UUID) -> dict | None:
        """Return workflow with statuses and transitions, or None."""
        row = self._session.get(WorkflowRow, workflow_id)
        if row is None:
            return None
        statuses = self._session.scalars(
            select(WorkflowStatusRow)
            .where(WorkflowStatusRow.workflow_id == workflow_id)
            .order_by(WorkflowStatusRow.position)
        ).all()
        transitions = self._session.scalars(
            select(WorkflowTransitionRow).where(WorkflowTransitionRow.workflow_id == workflow_id)
        ).all()
        return {
            "id": row.id,
            "name": row.name,
            "statuses": [
                {
                    "key": s.key,
                    "name": s.name,
                    "is_initial": s.is_initial,
                    "position": s.position,
                }
                for s in statuses
            ],
            "transitions": [
                {
                    "from_status_key": t.from_status_key,
                    "to_status_key": t.to_status_key,
                    "name": t.name,
                }
                for t in transitions
            ],
        }

    def list_workflows(self) -> list[dict]:
        """List all workflows (summary)."""
        rows = self._session.scalars(select(WorkflowRow).order_by(WorkflowRow.name)).all()
        return [{"id": r.id, "name": r.name} for r in rows]

    def create_task_type(
        self,
        *,
        key: str,
        name: str,
        workflow_id: UUID,
        hierarchy_level: str,
        now: datetime,
    ) -> UUID:
        """Insert a task type; return id."""
        type_id = uuid4()
        self._session.add(
            TaskTypeRow(
                id=type_id,
                key=key,
                name=name,
                workflow_id=workflow_id,
                hierarchy_level=hierarchy_level,
                is_active=True,
                created_at=now,
            )
        )
        self._session.flush()
        return type_id

    def get_task_type(self, task_type_id: UUID) -> TaskTypeRow | None:
        """Load a task type row."""
        return self._session.get(TaskTypeRow, task_type_id)

    def get_task_type_by_key(self, key: str) -> TaskTypeRow | None:
        """Load a task type by unique key."""
        return self._session.scalar(select(TaskTypeRow).where(TaskTypeRow.key == key))

    def list_task_types(self, *, active_only: bool = False) -> list[TaskTypeRow]:
        """List task types."""
        stmt: Select[tuple[TaskTypeRow]] = select(TaskTypeRow).order_by(TaskTypeRow.key)
        if active_only:
            stmt = stmt.where(TaskTypeRow.is_active.is_(True))
        return list(self._session.scalars(stmt).all())

    def set_task_type_active(self, task_type_id: UUID, is_active: bool) -> None:
        """Activate or deactivate a task type."""
        row = self._session.get(TaskTypeRow, task_type_id)
        if row is not None:
            row.is_active = is_active

    def initial_status_key(self, workflow_id: UUID) -> str | None:
        """Return the initial status key for a workflow."""
        row = self._session.scalar(
            select(WorkflowStatusRow).where(
                WorkflowStatusRow.workflow_id == workflow_id,
                WorkflowStatusRow.is_initial.is_(True),
            )
        )
        return row.key if row else None

    def transition_targets(self, workflow_id: UUID, from_status_key: str) -> set[str]:
        """Allowed next status keys from the current status."""
        rows = self._session.scalars(
            select(WorkflowTransitionRow).where(
                WorkflowTransitionRow.workflow_id == workflow_id,
                WorkflowTransitionRow.from_status_key == from_status_key,
            )
        ).all()
        return {r.to_status_key for r in rows}

    # --- tasks ---

    def allocate_task_sequence(self, task_type_id: UUID) -> int:
        """Reserve the next per-type sequence number (locked for concurrency)."""
        row = self._session.get(
            TaskTypeSequenceRow,
            task_type_id,
            with_for_update=True,
        )
        if row is None:
            max_existing = self._session.scalar(
                select(func.coalesce(func.max(TaskRow.sequence_number), 0)).where(
                    TaskRow.task_type_id == task_type_id
                )
            )
            next_value = int(max_existing or 0) + 1
            row = TaskTypeSequenceRow(task_type_id=task_type_id, next_value=next_value + 1)
            self._session.add(row)
            self._session.flush()
            return next_value
        assigned = row.next_value
        row.next_value = assigned + 1
        self._session.flush()
        return assigned

    def save_task(self, task: Task) -> None:
        """Insert or update a task and replace child collections."""
        row = self._session.get(TaskRow, task.id)
        if row is None:
            row = TaskRow(
                id=task.id,
                task_type_id=task.task_type_id,
                status_key=task.status_key,
                title=task.title,
                description=task.description,
                assignee_user_id=task.assignee_user_id.value if task.assignee_user_id else None,
                parent_task_id=task.parent_task_id,
                due_on=task.due_on,
                priority=task.priority,
                reference=task.reference,
                sequence_number=task.sequence_number,
                created_by=task.created_by.value,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            self._session.add(row)
        else:
            row.status_key = task.status_key
            row.title = task.title
            row.description = task.description
            row.assignee_user_id = (
                task.assignee_user_id.value if task.assignee_user_id else None
            )
            row.due_on = task.due_on
            row.priority = task.priority
            row.updated_at = task.updated_at
            # reference + sequence_number are immutable after create

        self._session.flush()
        # replace children
        for model in (
            TaskStepRow,
            TaskCommentRow,
            TaskAttachmentRow,
            TaskEntityLinkRow,
            TaskFollowerRow,
        ):
            existing = self._session.scalars(
                select(model).where(model.task_id == task.id)  # type: ignore[attr-defined]
            ).all()
            for item in existing:
                self._session.delete(item)
        self._session.flush()

        for step in task.steps:
            self._session.add(
                TaskStepRow(
                    id=step.id,
                    task_id=task.id,
                    title=step.title,
                    position=step.position,
                    is_done=step.is_done,
                )
            )
        for comment in task.comments:
            self._session.add(
                TaskCommentRow(
                    id=comment.id,
                    task_id=task.id,
                    author_user_id=comment.author_user_id.value,
                    body=comment.body,
                    created_at=comment.created_at,
                )
            )
        for att in task.attachments:
            self._session.add(
                TaskAttachmentRow(
                    id=att.id,
                    task_id=task.id,
                    filename=att.filename,
                    content_type=att.content_type,
                    size_bytes=att.size_bytes,
                    storage_key=att.storage_key,
                    uploaded_by=att.uploaded_by.value,
                    created_at=att.created_at,
                )
            )
        for link in task.entity_links:
            self._session.add(
                TaskEntityLinkRow(
                    id=uuid4(),
                    task_id=task.id,
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                )
            )
        for follower in task.follower_user_ids:
            self._session.add(
                TaskFollowerRow(
                    id=uuid4(),
                    task_id=task.id,
                    user_id=follower.value,
                )
            )
        self._session.flush()

    def get_task(self, task_id: UUID) -> Task | None:
        """Load a task aggregate."""
        row = self._session.get(TaskRow, task_id)
        if row is None:
            return None
        return self._to_task(row)

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
        """Page tasks with optional filters."""
        stmt = select(TaskRow)
        count_stmt = select(func.count()).select_from(TaskRow)
        if assignee_user_id is not None:
            stmt = stmt.where(TaskRow.assignee_user_id == assignee_user_id)
            count_stmt = count_stmt.where(TaskRow.assignee_user_id == assignee_user_id)
        if status_key:
            stmt = stmt.where(TaskRow.status_key == status_key)
            count_stmt = count_stmt.where(TaskRow.status_key == status_key)
        if task_type_id is not None:
            stmt = stmt.where(TaskRow.task_type_id == task_type_id)
            count_stmt = count_stmt.where(TaskRow.task_type_id == task_type_id)
        if priority:
            stmt = stmt.where(TaskRow.priority == priority)
            count_stmt = count_stmt.where(TaskRow.priority == priority)
        if due_on_from is not None:
            stmt = stmt.where(TaskRow.due_on >= due_on_from)
            count_stmt = count_stmt.where(TaskRow.due_on >= due_on_from)
        if due_on_to is not None:
            stmt = stmt.where(TaskRow.due_on <= due_on_to)
            count_stmt = count_stmt.where(TaskRow.due_on <= due_on_to)
        needle = (q or "").strip()
        if needle:
            pattern = f"%{needle}%"
            text_match = or_(
                TaskRow.title.ilike(pattern),
                TaskRow.reference.ilike(pattern),
                TaskRow.description.ilike(pattern),
            )
            stmt = stmt.where(text_match)
            count_stmt = count_stmt.where(text_match)
        total = int(self._session.scalar(count_stmt) or 0)
        rows = self._session.scalars(
            stmt.order_by(TaskRow.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [self._to_task(r) for r in rows], total

    def add_task_link(self, *, from_task_id: UUID, to_task_id: UUID, link_type: str) -> UUID:
        """Create a peer task link."""
        link_id = uuid4()
        self._session.add(
            TaskLinkRow(
                id=link_id,
                from_task_id=from_task_id,
                to_task_id=to_task_id,
                link_type=link_type,
            )
        )
        self._session.flush()
        return link_id

    def list_task_links(self, task_id: UUID) -> list[dict]:
        """Links where the task is either end."""
        rows = self._session.scalars(
            select(TaskLinkRow).where(
                (TaskLinkRow.from_task_id == task_id) | (TaskLinkRow.to_task_id == task_id)
            )
        ).all()
        return [
            {
                "id": r.id,
                "from_task_id": r.from_task_id,
                "to_task_id": r.to_task_id,
                "link_type": r.link_type,
            }
            for r in rows
        ]

    def _to_task(self, row: TaskRow) -> Task:
        steps = self._session.scalars(
            select(TaskStepRow)
            .where(TaskStepRow.task_id == row.id)
            .order_by(TaskStepRow.position)
        ).all()
        comments = self._session.scalars(
            select(TaskCommentRow)
            .where(TaskCommentRow.task_id == row.id)
            .order_by(TaskCommentRow.created_at)
        ).all()
        attachments = self._session.scalars(
            select(TaskAttachmentRow).where(TaskAttachmentRow.task_id == row.id)
        ).all()
        links = self._session.scalars(
            select(TaskEntityLinkRow).where(TaskEntityLinkRow.task_id == row.id)
        ).all()
        followers = self._session.scalars(
            select(TaskFollowerRow).where(TaskFollowerRow.task_id == row.id)
        ).all()
        return Task(
            id=row.id,
            task_type_id=row.task_type_id,
            status_key=row.status_key,
            title=row.title,
            description=row.description,
            assignee_user_id=UserId(row.assignee_user_id) if row.assignee_user_id else None,
            created_by=UserId(row.created_by),
            created_at=row.created_at,
            updated_at=row.updated_at,
            parent_task_id=row.parent_task_id,
            due_on=row.due_on,
            priority=row.priority or "normal",
            reference=row.reference or "",
            sequence_number=row.sequence_number or 0,
            steps=[
                TaskStep(id=s.id, title=s.title, position=s.position, is_done=s.is_done)
                for s in steps
            ],
            comments=[
                TaskComment(
                    id=c.id,
                    author_user_id=UserId(c.author_user_id),
                    body=c.body,
                    created_at=c.created_at,
                )
                for c in comments
            ],
            attachments=[
                TaskAttachment(
                    id=a.id,
                    filename=a.filename,
                    content_type=a.content_type,
                    size_bytes=a.size_bytes,
                    storage_key=a.storage_key,
                    uploaded_by=UserId(a.uploaded_by),
                    created_at=a.created_at,
                )
                for a in attachments
            ],
            entity_links=[
                EntityLink(entity_type=l.entity_type, entity_id=l.entity_id) for l in links
            ],
            follower_user_ids=[UserId(f.user_id) for f in followers],
        )

