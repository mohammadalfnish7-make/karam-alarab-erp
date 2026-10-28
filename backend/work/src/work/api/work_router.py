from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response as FastAPIResponse

from application.actor import Actor
from work.api.deps import get_work_service, require_permission
from work.api.work_dto import (
    AddCommentRequest,
    AddEntityLinkRequest,
    AddFollowerRequest,
    AddStepRequest,
    AddTaskLinkRequest,
    AssignTaskRequest,
    CompleteStepRequest,
    CreateTaskRequest,
    CreateTaskTypeRequest,
    CreateWorkflowRequest,
    PatchTaskRequest,
    PatchTaskTypeRequest,
    RemindTaskRequest,
    RenameStepRequest,
    TransitionTaskRequest,
)
from work.application.work_service import WorkService
from work.domain.task import Task

router = APIRouter(tags=["work"])


def _task_json(task: Task) -> dict[str, Any]:
    """Serialize a Task aggregate for HTTP."""
    return {
        "id": str(task.id),
        "taskTypeId": str(task.task_type_id),
        "reference": task.reference,
        "sequenceNumber": task.sequence_number,
        "statusKey": task.status_key,
        "title": task.title,
        "description": task.description,
        "assigneeUserId": str(task.assignee_user_id) if task.assignee_user_id else None,
        "parentTaskId": str(task.parent_task_id) if task.parent_task_id else None,
        "dueOn": task.due_on.isoformat() if task.due_on else None,
        "priority": task.priority,
        "createdBy": str(task.created_by),
        "createdAt": task.created_at.isoformat(),
        "updatedAt": task.updated_at.isoformat(),
        "steps": [
            {
                "id": str(s.id),
                "title": s.title,
                "position": s.position,
                "isDone": s.is_done,
            }
            for s in task.steps
        ],
        "comments": [
            {
                "id": str(c.id),
                "authorUserId": str(c.author_user_id),
                "body": c.body,
                "createdAt": c.created_at.isoformat(),
            }
            for c in task.comments
        ],
        "attachments": [
            {
                "id": str(a.id),
                "filename": a.filename,
                "contentType": a.content_type,
                "sizeBytes": a.size_bytes,
                "createdAt": a.created_at.isoformat(),
            }
            for a in task.attachments
        ],
        "entityLinks": [
            {"entityType": e.entity_type, "entityId": e.entity_id} for e in task.entity_links
        ],
        "followerUserIds": [str(uid) for uid in task.follower_user_ids],
    }


@router.post("/workflows", status_code=201)
def create_workflow(
    body: CreateWorkflowRequest,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Admin: create a workflow graph."""
    return work.create_workflow(
        name=body.name,
        statuses=[s.model_dump() for s in body.statuses],
        transitions=[t.model_dump() for t in body.transitions],
    )


@router.get("/workflows")
def list_workflows(
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> list[dict[str, Any]]:
    """List workflows."""
    rows = work.list_workflows()
    return [{"id": str(r["id"]), "name": r["name"]} for r in rows]


@router.get("/workflows/{workflow_id}")
def get_workflow(
    workflow_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Get one workflow with statuses and transitions."""
    row = work.get_workflow(workflow_id)
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "statuses": row["statuses"],
        "transitions": row["transitions"],
    }


@router.post("/task-types", status_code=201)
def create_task_type(
    body: CreateTaskTypeRequest,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Admin: register a task type (clients fetch these later)."""
    row = work.create_task_type(
        key=body.key,
        name=body.name,
        workflow_id=body.workflow_id,
        hierarchy_level=body.hierarchy_level,
    )
    return {
        "id": str(row["id"]),
        "key": row["key"],
        "name": row["name"],
        "workflowId": str(row["workflow_id"]),
        "hierarchyLevel": row["hierarchy_level"],
        "isActive": row["is_active"],
    }


@router.get("/task-types")
def list_task_types(
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
    active_only: Annotated[bool, Query(alias="activeOnly")] = False,
) -> list[dict[str, Any]]:
    """Fetch task types for create forms / admin."""
    rows = work.list_task_types(active_only=active_only)
    return [
        {
            "id": str(r["id"]),
            "key": r["key"],
            "name": r["name"],
            "workflowId": str(r["workflow_id"]),
            "hierarchyLevel": r["hierarchy_level"],
            "isActive": r["is_active"],
        }
        for r in rows
    ]


@router.patch("/task-types/{task_type_id}")
def patch_task_type(
    task_type_id: UUID,
    body: PatchTaskTypeRequest,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Admin: activate or deactivate a task type."""
    row = work.set_task_type_active(task_type_id, is_active=body.is_active)
    return {
        "id": str(row["id"]),
        "key": row["key"],
        "name": row["name"],
        "workflowId": str(row["workflow_id"]),
        "hierarchyLevel": row["hierarchy_level"],
        "isActive": row["is_active"],
    }


@router.get("/task-assignees")
def list_task_assignees(
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> list[dict[str, str]]:
    """Active staff for assignee and follower pickers."""
    return work.list_assignees()


@router.post("/tasks", status_code=201)
def create_task(
    body: CreateTaskRequest,
    actor: Annotated[Actor, Depends(require_permission("work:create"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Create a task of an admin-defined type."""
    task = work.create_task(
        actor,
        task_type_id=body.task_type_id,
        title=body.title,
        description=body.description,
        assignee_user_id=body.assignee_user_id,
        parent_task_id=body.parent_task_id,
        due_on=body.due_on,
        priority=body.priority,
        follower_user_ids=body.follower_user_ids,
    )
    return _task_json(task)


@router.get("/tasks")
def list_tasks(
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
    assignee_user_id: Annotated[UUID | None, Query(alias="assigneeUserId")] = None,
    status_key: Annotated[str | None, Query(alias="statusKey")] = None,
    task_type_id: Annotated[UUID | None, Query(alias="taskTypeId")] = None,
    priority: Annotated[str | None, Query()] = None,
    due_on_from: Annotated[date | None, Query(alias="dueOnFrom")] = None,
    due_on_to: Annotated[date | None, Query(alias="dueOnTo")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> dict[str, Any]:
    """List tasks with filters. Omit assigneeUserId to list across all assignees."""
    items, total = work.list_tasks(
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
    return {
        "data": [_task_json(t) for t in items],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.get("/tasks/{task_id}")
def get_task(
    task_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Get one task."""
    return _task_json(work.get_task(task_id))


@router.post("/tasks/{task_id}/transitions", status_code=200)
def transition_task(
    task_id: UUID,
    body: TransitionTaskRequest,
    actor: Annotated[Actor, Depends(require_permission("work:transition"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Transition task status via workflow edge."""
    return _task_json(
        work.transition_task(actor, task_id, to_status_key=body.to_status_key)
    )


@router.patch("/tasks/{task_id}/assignee")
def assign_task(
    task_id: UUID,
    body: AssignTaskRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Assign or unassign a task (fires notify when assigned)."""
    return _task_json(
        work.assign_task(actor, task_id, assignee_user_id=body.assignee_user_id)
    )


@router.patch("/tasks/{task_id}")
def patch_task(
    task_id: UUID,
    body: PatchTaskRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Patch due date and/or priority."""
    kwargs: dict[str, Any] = {}
    if "due_on" in body.model_fields_set:
        kwargs["due_on"] = body.due_on
    if "priority" in body.model_fields_set and body.priority is not None:
        kwargs["priority"] = body.priority
    if not kwargs:
        return _task_json(work.get_task(task_id))
    return _task_json(work.patch_task(actor, task_id, **kwargs))


@router.post("/tasks/{task_id}/steps", status_code=201)
def add_step(
    task_id: UUID,
    body: AddStepRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Add a checklist step (task creator only)."""
    return _task_json(work.add_step(actor, task_id, title=body.title))


@router.patch("/tasks/{task_id}/steps/{step_id}")
def complete_step(
    task_id: UUID,
    step_id: UUID,
    body: CompleteStepRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Complete or reopen a step."""
    return _task_json(
        work.complete_step(actor, task_id, step_id, is_done=body.is_done)
    )


@router.put("/tasks/{task_id}/steps/{step_id}")
def rename_step(
    task_id: UUID,
    step_id: UUID,
    body: RenameStepRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Rename a checklist step (task creator only)."""
    return _task_json(
        work.rename_step(actor, task_id, step_id, title=body.title)
    )


@router.delete("/tasks/{task_id}/steps/{step_id}")
def delete_step(
    task_id: UUID,
    step_id: UUID,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Delete a checklist step (task creator only)."""
    return _task_json(work.delete_step(actor, task_id, step_id))


@router.post("/tasks/{task_id}/comments", status_code=201)
def add_comment(
    task_id: UUID,
    body: AddCommentRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Add a comment."""
    return _task_json(work.add_comment(actor, task_id, body=body.body))


@router.post("/tasks/{task_id}/attachments", status_code=201)
async def add_attachment(
    task_id: UUID,
    actor: Annotated[Actor, Depends(require_permission("work:attach"))],
    work: Annotated[WorkService, Depends(get_work_service)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload a file attachment."""
    data = await file.read()
    return _task_json(
        work.add_attachment(
            actor,
            task_id,
            filename=file.filename or "upload.bin",
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    )


@router.get("/tasks/{task_id}/attachments/{attachment_id}")
def download_attachment(
    task_id: UUID,
    attachment_id: UUID,
    _: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> FastAPIResponse:
    """Download attachment bytes."""
    task, data = work.read_attachment_bytes(task_id, attachment_id)
    att = next(a for a in task.attachments if a.id == attachment_id)
    return FastAPIResponse(
        content=data,
        media_type=att.content_type,
        headers={"Content-Disposition": f'attachment; filename="{att.filename}"'},
    )


@router.post("/tasks/{task_id}/followers", status_code=201)
def add_follower(
    task_id: UUID,
    body: AddFollowerRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Add a follower who can remind the assignee."""
    return _task_json(
        work.add_follower(actor, task_id, follower_user_id=body.follower_user_id)
    )


@router.delete("/tasks/{task_id}/followers/{follower_user_id}", status_code=200)
def remove_follower(
    task_id: UUID,
    follower_user_id: UUID,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Remove a follower."""
    return _task_json(
        work.remove_follower(actor, task_id, follower_user_id=follower_user_id)
    )


@router.post("/tasks/{task_id}/reminders", status_code=200)
def remind_assignee(
    task_id: UUID,
    body: RemindTaskRequest,
    actor: Annotated[Actor, Depends(require_permission("work:read"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Follower reminds the assignee (in-app + webhooks)."""
    return _task_json(work.remind_assignee(actor, task_id, message=body.message))


@router.post("/tasks/{task_id}/entity-links", status_code=201)
def add_entity_link(
    task_id: UUID,
    body: AddEntityLinkRequest,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Link an ERP entity to the task."""
    return _task_json(
        work.add_entity_link(
            actor,
            task_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
    )


@router.delete("/tasks/{task_id}/entity-links/{entity_type}/{entity_id}")
def remove_entity_link(
    task_id: UUID,
    entity_type: str,
    entity_id: str,
    actor: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Unlink an ERP entity from the task (catalog file stays in the catalog)."""
    return _task_json(
        work.remove_entity_link(
            actor,
            task_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )


@router.delete("/tasks/{task_id}/attachments/{attachment_id}")
def remove_attachment(
    task_id: UUID,
    attachment_id: UUID,
    actor: Annotated[Actor, Depends(require_permission("work:attach"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Remove a direct task attachment."""
    return _task_json(work.remove_attachment(actor, task_id, attachment_id))


@router.post("/tasks/{task_id}/links", status_code=201)
def add_task_link(
    task_id: UUID,
    body: AddTaskLinkRequest,
    _: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> list[dict[str, Any]]:
    """Create a peer task link."""
    links = work.add_task_link(
        task_id, to_task_id=body.to_task_id, link_type=body.link_type
    )
    return [
        {
            "id": str(l["id"]),
            "fromTaskId": str(l["from_task_id"]),
            "toTaskId": str(l["to_task_id"]),
            "linkType": l["link_type"],
        }
        for l in links
    ]
