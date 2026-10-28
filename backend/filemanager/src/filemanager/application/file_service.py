from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from domain.shared.clock import Clock
from domain.shared.domain_error import NotFoundError, ValidationError
from domain.shared.file_catalog import CatalogFile
from domain.shared.user_id import UserId
from filemanager.database.repositories.file_repository import SqlAlchemyFileRepository
from filemanager.domain.stored_file import StoredFile
from filemanager.storage.local_blob_store import LocalBlobStore
from support.events import UnitOfWork


def to_catalog_file(stored: StoredFile) -> CatalogFile:
    """Map the aggregate to the port type other modules may hold."""
    return CatalogFile(
        id=stored.id,
        display_name=stored.display_name,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status=stored.status,
        uploaded_by=stored.uploaded_by.value,
        created_at=stored.created_at,
        owner_context=stored.owner_context,
        owner_id=stored.owner_id,
    )


class FileService:
    """Register a file, search by name, and read bytes. One aggregate per commit."""

    def __init__(
        self,
        *,
        files: SqlAlchemyFileRepository,
        blobs: LocalBlobStore,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        """Wire the catalog repository, blob folder, clock, and unit of work."""
        self._files = files
        self._blobs = blobs
        self._clock = clock
        self._uow = uow

    def register(
        self,
        *,
        uploaded_by: UserId,
        actor_email: str,
        display_name: str,
        content_type: str,
        data: bytes,
        owner_context: str = "",
        owner_id: str = "",
    ) -> CatalogFile:
        """Store bytes, then the catalog row. A failed commit removes the blob."""
        stored = StoredFile.register(
            display_name=display_name,
            content_type=content_type,
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
            uploaded_by=uploaded_by,
            actor_email=actor_email,
            now=self._clock.now(),
            owner_context=owner_context,
            owner_id=owner_id,
        )
        try:
            self._blobs.put(stored.storage_key, data)
            self._files.add(stored)
            self._uow.collect(stored.pull_events())
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            self._blobs.delete(stored.storage_key)
            raise
        return to_catalog_file(stored)

    def search_by_name(
        self,
        name: str,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[CatalogFile], int]:
        """Find available files whose display name contains `name`."""
        query = name.strip()
        if not query:
            raise ValidationError(
                "Name is required.",
                fields={"name": "Enter part of the file name."},
            )
        rows, total = self._files.search_by_name(query, page=page, page_size=page_size)
        return [to_catalog_file(row) for row in rows], total

    def get(self, file_id: UUID) -> CatalogFile:
        """Load one available file. Missing ids are not found."""
        stored = self._files.get(file_id)
        if stored is None:
            raise NotFoundError("File not found.")
        return to_catalog_file(stored)

    def read_content(self, file_id: UUID) -> tuple[CatalogFile, bytes]:
        """Load metadata and bytes for a download."""
        stored = self._files.get(file_id)
        if stored is None:
            raise NotFoundError("File not found.")
        data = self._blobs.get(stored.storage_key)
        return to_catalog_file(stored), data


def build_file_service(
    *,
    session,  # noqa: ANN001
    uow: UnitOfWork,
    upload_dir: Path,
    clock: Clock,
) -> FileService:
    """Composition helper used by the app factory."""
    return FileService(
        files=SqlAlchemyFileRepository(session),
        blobs=LocalBlobStore(upload_dir / "catalog"),
        clock=clock,
        uow=uow,
    )
