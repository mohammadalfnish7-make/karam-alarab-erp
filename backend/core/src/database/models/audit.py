from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from database.engine import Base


class AuditEntryRow(Base):
    """Append-only audit log row for identity events."""

    __tablename__ = "audit_entries"

    id: Mapped[object] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    actor: Mapped[str] = mapped_column(String(320), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="-")
