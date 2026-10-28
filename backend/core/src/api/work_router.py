from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response as FastAPIResponse

from api.deps import get_work_service, require_permission
from api.work_dto import (
    AddCommentRequest,
    AddEntityLinkRequest,
    AddStepRequest,
    AddTaskLinkRequest,
    AssignTaskRequest,
    CompleteStepRequest,
    CreateTaskRequest,
    CreateTaskTypeRequest,
    CreateWorkflowRequest,
    PatchTaskTypeRequest,
    TransitionTaskRequest,
)
from application.actor import Actor
from application.work_service import WorkService
from domain.work.task import Task

router = APIRouter(tags=["work"])


def _task_json(task: Task) -> dict[str, Any]:
    """Serialize a Task aggregate for HTTP."""
    return {
        "id": str(task.id),
        "taskTypeId": str(task.task_type_id),
        "statusKey": task.status_key,
        "title": task.title,
        "description": task.description,
        "assigneeUserId": str(task.assignee_user_id) if task.assignee_user_id else None,
        "parentTaskId": str(task.parent_task_id) if task.parent_task_id else None,
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
) -> dict[str, Any]:
    """List tasks with filters."""
    items, total = work.list_tasks(
        page=page,
        page_size=page_size,
        assignee_user_id=assignee_user_id,
        status_key=status_key,
        task_type_id=task_type_id,
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


@router.post("/tasks/{task_id}/steps", status_code=201)
def add_step(
    task_id: UUID,
    body: AddStepRequest,
    _: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Add a checklist step."""
    return _task_json(work.add_step(task_id, title=body.title))


@router.patch("/tasks/{task_id}/steps/{step_id}")
def complete_step(
    task_id: UUID,
    step_id: UUID,
    body: CompleteStepRequest,
    _: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Complete or reopen a step."""
    return _task_json(work.complete_step(task_id, step_id, is_done=body.is_done))


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


@router.post("/tasks/{task_id}/entity-links", status_code=201)
def add_entity_link(
    task_id: UUID,
    body: AddEntityLinkRequest,
    _: Annotated[Actor, Depends(require_permission("work:update"))],
    work: Annotated[WorkService, Depends(get_work_service)],
) -> dict[str, Any]:
    """Link an ERP entity to the task."""
    return _task_json(
        work.add_entity_link(
            task_id, entity_type=body.entity_type, entity_id=body.entity_id
        )
    )


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
