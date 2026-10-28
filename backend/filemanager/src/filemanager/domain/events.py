from __future__ import annotations

from dataclasses import dataclass

from domain.shared.domain_event import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class FileRegistered(DomainEvent):
    """A file was stored and is available to search by name."""

    actor_email: str = ""
    display_name: str = ""
    summary: str = ""
