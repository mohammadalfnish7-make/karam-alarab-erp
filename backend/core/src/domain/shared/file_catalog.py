from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.shared.user_id import UserId


@dataclass(frozen=True, slots=True)
class CatalogFile:
    """File metadata a module may store by id. The storage key is not included."""

    id: UUID
    display_name: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    uploaded_by: UUID
    created_at: datetime
    owner_context: str
    owner_id: str


class FileCatalog(Protocol):
    """Port modules use. The implementation lives in filemanager, wired by main."""

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
        """Store a file and return its catalog record."""
        ...

    def search_by_name(
        self,
        name: str,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[CatalogFile], int]:
        """Find files whose display name contains `name`."""
        ...

    def get(self, file_id: UUID) -> CatalogFile:
        """Load one file the caller is allowed to know about."""
        ...

    def read_content(self, file_id: UUID) -> tuple[CatalogFile, bytes]:
        """Load metadata and bytes for a download."""
        ...
