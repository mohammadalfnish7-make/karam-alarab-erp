from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from api.deps import get_file_catalog, require_permission
from application.actor import Actor
from domain.shared.file_catalog import CatalogFile, FileCatalog
from filemanager.api.disposition import content_disposition
from filemanager.domain.stored_file import MAX_FILE_BYTES

router = APIRouter(tags=["files"])


def _file_json(stored: CatalogFile) -> dict[str, Any]:
    return {
        "id": str(stored.id),
        "displayName": stored.display_name,
        "contentType": stored.content_type,
        "sizeBytes": stored.size_bytes,
        "sha256": stored.sha256,
        "status": stored.status,
        "uploadedBy": str(stored.uploaded_by),
        "ownerContext": stored.owner_context,
        "ownerId": stored.owner_id,
        "createdAt": stored.created_at.isoformat(),
    }


@router.post("/files", status_code=201)
async def register_file(
    actor: Annotated[Actor, Depends(require_permission("files:write"))],
    catalog: Annotated[FileCatalog, Depends(get_file_catalog)],
    file: UploadFile = File(...),
    owner_context: Annotated[str, Form()] = "",
    owner_id: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    """Store a file in the shared catalog."""
    data = await file.read(MAX_FILE_BYTES + 1)
    stored = catalog.register(
        uploaded_by=actor.user_id,
        actor_email=actor.email,
        display_name=file.filename or "",
        content_type=file.content_type or "",
        data=data,
        owner_context=owner_context,
        owner_id=owner_id,
    )
    return _file_json(stored)


@router.get("/files")
def search_files(
    _: Annotated[Actor, Depends(require_permission("files:read"))],
    catalog: Annotated[FileCatalog, Depends(get_file_catalog)],
    name: Annotated[str, Query(min_length=1, max_length=255)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """Search available files by display name."""
    rows, total = catalog.search_by_name(name, page=page, page_size=page_size)
    return {
        "data": [_file_json(row) for row in rows],
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


@router.get("/files/{file_id}")
def get_file(
    file_id: UUID,
    _: Annotated[Actor, Depends(require_permission("files:read"))],
    catalog: Annotated[FileCatalog, Depends(get_file_catalog)],
) -> dict[str, Any]:
    """Return metadata for one file."""
    return _file_json(catalog.get(file_id))


@router.get("/files/{file_id}/content")
def download_file(
    file_id: UUID,
    _: Annotated[Actor, Depends(require_permission("files:read"))],
    catalog: Annotated[FileCatalog, Depends(get_file_catalog)],
) -> Response:
    """Download file bytes. The stored key is not the client filename."""
    stored, data = catalog.read_content(file_id)
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={
            "Content-Disposition": content_disposition(stored.display_name),
            "X-Content-Type-Options": "nosniff",
        },
    )
