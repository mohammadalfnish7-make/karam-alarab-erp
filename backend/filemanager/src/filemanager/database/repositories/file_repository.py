from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.shared.user_id import UserId
from filemanager.database.models.file_catalog import FileCatalogRow
from filemanager.domain.stored_file import STATUS_AVAILABLE, StoredFile


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_domain(row: FileCatalogRow) -> StoredFile:
    return StoredFile(
        id=row.id,
        display_name=row.display_name,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        storage_key=row.storage_key,
        status=row.status,
        uploaded_by=UserId(row.uploaded_by),
        created_at=row.created_at,
        owner_context=row.owner_context,
        owner_id=row.owner_id,
    )


class SqlAlchemyFileRepository:
    """Persist stored-file metadata. Search matches the display name only."""

    def __init__(self, session: Session) -> None:
        """Bind to the request DB session."""
        self._session = session

    def add(self, stored: StoredFile) -> None:
        """Insert one available file row."""
        self._session.add(
            FileCatalogRow(
                id=stored.id,
                display_name=stored.display_name,
                name_fold=stored.display_name.casefold(),
                content_type=stored.content_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_key=stored.storage_key,
                status=stored.status,
                uploaded_by=stored.uploaded_by.value,
                owner_context=stored.owner_context,
                owner_id=stored.owner_id,
                created_at=stored.created_at,
            )
        )
        self._session.flush()

    def get(self, file_id: UUID) -> StoredFile | None:
        """Load one file by id."""
        row = self._session.get(FileCatalogRow, file_id)
        if row is None or row.status != STATUS_AVAILABLE:
            return None
        return _to_domain(row)

    def search_by_name(
        self,
        name: str,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[StoredFile], int]:
        """Case-insensitive contains match on the display name."""
        pattern = f"%{_escape_like(name.casefold())}%"
        name_match = FileCatalogRow.name_fold.like(pattern, escape="\\")
        available = FileCatalogRow.status == STATUS_AVAILABLE
        total = self._session.scalar(
            select(func.count()).select_from(FileCatalogRow).where(name_match, available)
        )
        rows = self._session.scalars(
            select(FileCatalogRow)
            .where(name_match, available)
            .order_by(FileCatalogRow.created_at.desc(), FileCatalogRow.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [_to_domain(row) for row in rows], int(total or 0)
