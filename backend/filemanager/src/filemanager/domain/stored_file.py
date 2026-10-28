from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from domain.shared.domain_error import ValidationError
from domain.shared.domain_event import DomainEvent
from domain.shared.user_id import UserId
from filemanager.domain.content import content_matches_type, normalize_content_type
from filemanager.domain.events import FileRegistered

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_DISPLAY_NAME = 255
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/plain",
        "application/json",
    }
)
STATUS_AVAILABLE = "available"

_OWNER_CONTEXT = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_OWNER_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def clean_display_name(raw: str) -> str:
    """Keep the final path segment and reject empty or control-only names."""
    segment = raw.replace("\\", "/").split("/")[-1].strip()
    name = "".join(ch for ch in segment if ch.isprintable())
    name = name.strip()
    if name in {"", ".", ".."}:
        raise ValidationError(
            "Filename is required.",
            fields={"filename": "Filename is required."},
        )
    if len(name) > MAX_DISPLAY_NAME:
        raise ValidationError(
            "Filename is too long.",
            fields={"filename": f"Use at most {MAX_DISPLAY_NAME} characters."},
        )
    return name


def clean_owner(owner_context: str, owner_id: str) -> tuple[str, str]:
    """Require both link fields, or neither. The catalog does not validate the target."""
    context = owner_context.strip()
    linked_id = owner_id.strip()
    if not context and not linked_id:
        return "", ""
    if not context or not linked_id:
        raise ValidationError(
            "Owner context and owner id are both required when linking a file.",
            fields={
                "owner_context": "Provide both owner context and owner id, or leave both empty.",
                "owner_id": "Provide both owner context and owner id, or leave both empty.",
            },
        )
    if _OWNER_CONTEXT.fullmatch(context) is None:
        raise ValidationError(
            "Owner context must be a short lowercase name such as freight or work.",
            fields={"owner_context": "Use a lowercase name such as freight or work."},
        )
    if _OWNER_ID.fullmatch(linked_id) is None:
        raise ValidationError(
            "Owner id is not valid.",
            fields={"owner_id": "Use letters, numbers, and . _ : - only."},
        )
    return context, linked_id


@dataclass
class StoredFile:
    """One available file in the shared catalog. Bytes are not on this object."""

    id: UUID
    display_name: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    status: str
    uploaded_by: UserId
    created_at: datetime
    owner_context: str = ""
    owner_id: str = ""
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @staticmethod
    def register(
        *,
        display_name: str,
        content_type: str,
        data: bytes,
        sha256: str,
        uploaded_by: UserId,
        actor_email: str,
        now: datetime,
        owner_context: str = "",
        owner_id: str = "",
    ) -> StoredFile:
        """Accept a file that passes name, size, type, and content checks."""
        name = clean_display_name(display_name)
        declared = normalize_content_type(content_type or "")
        size_bytes = len(data)
        if size_bytes <= 0:
            raise ValidationError(
                "Empty files are not allowed.",
                fields={"file": "Empty files are not allowed."},
            )
        if size_bytes > MAX_FILE_BYTES:
            raise ValidationError(
                "File is too large.",
                fields={"file": "File is too large."},
            )
        if declared not in ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
            raise ValidationError(
                "File type is not allowed.",
                fields={"file": f"Use one of: {allowed}."},
            )
        if not content_matches_type(declared, data):
            raise ValidationError(
                "File contents do not match the declared type.",
                fields={"file": "File contents do not match the declared type."},
            )
        digest = sha256.strip().lower()
        if _SHA256.fullmatch(digest) is None:
            raise ValidationError(
                "File checksum is not valid.",
                fields={"file": "File checksum is not valid."},
            )
        context, linked_id = clean_owner(owner_context, owner_id)
        file_id = uuid4()
        owner_note = f" for {context}:{linked_id}" if context else ""
        stored = StoredFile(
            id=file_id,
            display_name=name,
            content_type=declared,
            size_bytes=size_bytes,
            sha256=digest,
            storage_key=uuid4().hex,
            status=STATUS_AVAILABLE,
            uploaded_by=uploaded_by,
            created_at=now,
            owner_context=context,
            owner_id=linked_id,
        )
        stored._events.append(
            FileRegistered(
                aggregate_id=str(file_id),
                occurred_at=now,
                actor_email=actor_email,
                display_name=name,
                summary=f"Registered {name} ({size_bytes} bytes){owner_note}",
            )
        )
        return stored

    def pull_events(self) -> list[DomainEvent]:
        """Return and clear domain events raised by the last command."""
        events = list(self._events)
        self._events.clear()
        return events
