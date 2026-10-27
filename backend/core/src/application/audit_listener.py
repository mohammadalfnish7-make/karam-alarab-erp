from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from database.models.audit import AuditEntryRow
from domain.identity.events import (
    LoginFailed,
    UserDeactivated,
    UserPasswordChanged,
    UserRegistered,
    UserRolesChanged,
)
from domain.shared.domain_event import DomainEvent
from support.logging import request_id_var


class AuditListener:
    """Append an audit row after commit for identity events."""

    def __init__(self, session_factory: sessionmaker) -> None:
        """Keep a session factory to write audit rows after commit."""
        self._session_factory = session_factory

    def handle(self, event: DomainEvent) -> None:
        """Write one append-only audit entry for a known identity event."""
        actor = "system"
        action = type(event).__name__
        entity = "unknown"
        summary = ""
        entity_id = event.aggregate_id

        if isinstance(event, UserRegistered):
            entity = "user"
            actor = event.email
            summary = f"Registered with roles {','.join(event.roles)}"
        elif isinstance(event, UserDeactivated):
            entity = "user"
            actor = event.email
            summary = "User deactivated"
        elif isinstance(event, UserRolesChanged):
            entity = "user"
            actor = event.email
            summary = f"Roles set to {','.join(event.roles)}"
        elif isinstance(event, UserPasswordChanged):
            entity = "user"
            actor = event.email
            summary = "Password changed"
        elif isinstance(event, LoginFailed):
            entity = "session"
            actor = event.email
            summary = f"Login failed: {event.reason}"
        else:
            return

        session = self._session_factory()
        try:
            session.add(
                AuditEntryRow(
                    occurred_at=event.occurred_at,
                    actor=actor,
                    action=action,
                    entity=entity,
                    entity_id=entity_id,
                    summary=summary,
                    request_id=request_id_var.get("-"),
                )
            )
            session.commit()
        finally:
            session.close()
