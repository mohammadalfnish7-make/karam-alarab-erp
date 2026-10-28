from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, require_permission
from application.actor import Actor
from database.models.trace import ProcessTraceRow, ProcessTraceStepRow
from database.repositories.trace_repository import SqlAlchemyTraceRepository
from domain.shared.domain_error import NotFoundError

router = APIRouter(tags=["process-traces"])


def _step_json(step: ProcessTraceStepRow) -> dict[str, Any]:
    """Serialize one trace step for HTTP."""
    try:
        detail = json.loads(step.detail_json or "{}")
    except json.JSONDecodeError:
        detail = {}
    return {
        "id": str(step.id),
        "stepKey": step.step_key,
        "status": step.status,
        "summary": step.summary,
        "detail": detail,
        "durationMs": step.duration_ms,
        "createdAt": step.created_at.isoformat(),
    }


def _trace_json(
    row: ProcessTraceRow, steps: list[ProcessTraceStepRow] | None = None
) -> dict[str, Any]:
    """Serialize a process trace (optionally with steps)."""
    data: dict[str, Any] = {
        "id": str(row.id),
        "correlationId": row.correlation_id,
        "requestId": row.request_id,
        "context": row.context,
        "operation": row.operation,
        "entityType": row.entity_type,
        "entityId": row.entity_id,
        "status": row.status,
        "summary": row.summary,
        "errorMessage": row.error_message,
        "createdAt": row.created_at.isoformat(),
        "finishedAt": row.finished_at.isoformat() if row.finished_at else None,
    }
    if steps is not None:
        data["steps"] = [_step_json(s) for s in steps]
    return data


@router.get("/process-traces")
def list_process_traces(
    _: Annotated[Actor, Depends(require_permission("process:read"))],
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
    context: Annotated[str | None, Query()] = None,
    operation: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query(alias="entityType")] = None,
    entity_id: Annotated[str | None, Query(alias="entityId")] = None,
    correlation_id: Annotated[str | None, Query(alias="correlationId")] = None,
    status: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """List process traces across all bounded contexts."""
    repo = SqlAlchemyTraceRepository(session)
    rows, total = repo.list_traces(
        page=page,
        page_size=page_size,
        context=context,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        status=status,
    )
    return {
        "data": [_trace_json(r) for r in rows],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.get("/process-traces/by-correlation/{correlation_id}")
def get_by_correlation(
    correlation_id: str,
    _: Annotated[Actor, Depends(require_permission("process:read"))],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """All traces sharing a correlation id, each with ordered steps."""
    repo = SqlAlchemyTraceRepository(session)
    rows = repo.list_by_correlation(correlation_id)
    return {
        "correlationId": correlation_id,
        "traces": [
            _trace_json(row, repo.list_steps(row.id)) for row in rows
        ],
    }


@router.get("/process-traces/{trace_id}")
def get_process_trace(
    trace_id: UUID,
    _: Annotated[Actor, Depends(require_permission("process:read"))],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """One process trace with ordered steps."""
    repo = SqlAlchemyTraceRepository(session)
    row = repo.get_trace(trace_id)
    if row is None:
        raise NotFoundError("Process trace not found.")
    return _trace_json(row, repo.list_steps(trace_id))
