from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ForbidModel(BaseModel):
    """Reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


class WorkflowStatusIn(ForbidModel):
    """One status when creating a workflow."""

    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    is_initial: bool = False


class WorkflowTransitionIn(ForbidModel):
    """One transition edge when creating a workflow."""

    from_status_key: str
    to_status_key: str
    name: str = ""


class CreateWorkflowRequest(ForbidModel):
    """Admin payload to define a workflow graph."""

    name: str = Field(min_length=1, max_length=128)
    statuses: list[WorkflowStatusIn] = Field(min_length=1)
    transitions: list[WorkflowTransitionIn] = Field(default_factory=list)


class CreateTaskTypeRequest(ForbidModel):
    """Admin payload to register a task type."""

    key: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    workflow_id: UUID
    hierarchy_level: str = "standard"


class PatchTaskTypeRequest(ForbidModel):
    """Activate or deactivate a task type."""

    is_active: bool


class CreateTaskRequest(ForbidModel):
    """Create a task from an admin-defined type."""

    task_type_id: UUID
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    assignee_user_id: UUID | None = None
    parent_task_id: UUID | None = None
    due_on: date | None = None
    priority: str = "normal"
    follower_user_ids: list[UUID] = Field(default_factory=list)


class AddFollowerRequest(ForbidModel):
    """Add a task follower."""

    follower_user_id: UUID


class RemindTaskRequest(ForbidModel):
    """Optional note when a follower reminds the assignee."""

    message: str = ""


class PatchTaskRequest(ForbidModel):
    """Patch due date and/or priority."""

    due_on: date | None = None
    priority: str | None = None


class TransitionTaskRequest(ForbidModel):
    """Move a task to another workflow status."""

    to_status_key: str = Field(min_length=1, max_length=64)


class AssignTaskRequest(ForbidModel):
    """Set or clear the assignee."""

    assignee_user_id: UUID | None = None


class AddStepRequest(ForbidModel):
    """Add a checklist step."""

    title: str = Field(min_length=1, max_length=500)


class CompleteStepRequest(ForbidModel):
    """Mark a step done/undone."""

    is_done: bool = True


class RenameStepRequest(ForbidModel):
    """Change a checklist step title."""

    title: str = Field(min_length=1, max_length=500)


class AddCommentRequest(ForbidModel):
    """Add a comment body."""

    body: str = Field(min_length=1)


class AddEntityLinkRequest(ForbidModel):
    """Soft-link an ERP entity."""

    entity_type: str
    entity_id: str


class AddTaskLinkRequest(ForbidModel):
    """Peer-link another task."""

    to_task_id: UUID
    link_type: str

