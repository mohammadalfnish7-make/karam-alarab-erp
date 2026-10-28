from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db, require_permission
from application.actor import Actor
from database.models.audit import AuditEntryRow
from domain.shared.domain_error import ValidationError

router = APIRouter(tags=["audit"])


@router.get("/audit-entries")
def list_audit_entries(
    _: Annotated[Actor, Depends(require_permission("process:read"))],
    db: Annotated[Session, Depends(get_db)],
    entity: Annotated[str, Query(min_length=1)],
    entity_id: Annotated[str, Query(alias="entityId", min_length=1)],
) -> dict[str, Any]:
    """List audit rows for one entity. Both filters are required."""
    cleaned_entity = entity.strip()
    cleaned_id = entity_id.strip()
    if not cleaned_entity or not cleaned_id:
        raise ValidationError(
            "Entity and entity id are required.",
            fields={
                "entity": "Entity is required.",
                "entityId": "Entity id is required.",
            },
        )
    rows = db.scalars(
        select(AuditEntryRow)
        .where(
            AuditEntryRow.entity == cleaned_entity,
            AuditEntryRow.entity_id == cleaned_id,
        )
        .order_by(AuditEntryRow.occurred_at.desc())
    ).all()
    return {
        "data": [
            {
                "id": str(row.id),
                "occurredAt": row.occurred_at.isoformat(),
                "actor": row.actor,
                "action": row.action,
                "entity": row.entity,
                "entityId": row.entity_id,
                "summary": row.summary,
                "requestId": row.request_id,
            }
            for row in rows
        ]
    }
